"""Credential adapter tests use a fake native API, never the real user's store."""
import ctypes
from unittest.mock import Mock, patch
import unittest

from ai import credentials

FAKE_KEY = "synthetic-key-for-credential-tests"


class CredentialTests(unittest.TestCase):
    def test_save_uses_fixed_user_local_generic_credential_and_exact_bytes(self):
        captured = {}

        def write(pointer, flags):
            item = ctypes.cast(pointer, ctypes.POINTER(credentials._Credential)).contents
            captured.update(target=item.TargetName, kind=item.Type, persist=item.Persist,
                            value=ctypes.string_at(item.CredentialBlob, item.CredentialBlobSize), flags=flags)
            return 1

        api = Mock(CredWriteW=write)
        with patch.object(credentials, "_api", return_value=api):
            credentials.save_key(FAKE_KEY)
        self.assertEqual(captured, {"target": credentials._TARGET, "kind": 1, "persist": 2,
                                    "value": FAKE_KEY.encode("ascii"), "flags": 0})

    def test_load_releases_native_buffer_and_reads_only_own_target(self):
        blob = ctypes.create_string_buffer(FAKE_KEY.encode("ascii"))
        item = credentials._Credential()
        item.Type, item.TargetName, item.CredentialBlobSize = 1, credentials._TARGET, len(FAKE_KEY)
        item.CredentialBlob = ctypes.cast(blob, ctypes.POINTER(ctypes.c_byte))

        def read(target, kind, flags, output):
            self.assertEqual((target, kind, flags), (credentials._TARGET, 1, 0))
            ctypes.cast(output, ctypes.POINTER(ctypes.POINTER(credentials._Credential)))[0] = ctypes.pointer(item)
            return 1

        api = Mock(CredReadW=read)
        with patch.object(credentials, "is_supported", return_value=True), patch.object(credentials, "_api", return_value=api):
            self.assertEqual(credentials.load_key(), FAKE_KEY)
        api.CredFree.assert_called_once()

    def test_missing_key_and_idempotent_delete(self):
        api = Mock()
        api.CredReadW.return_value = api.CredDeleteW.return_value = 0
        with patch.object(credentials, "is_supported", return_value=True), patch.object(credentials, "_api", return_value=api), \
                patch.object(ctypes, "get_last_error", return_value=1168):
            self.assertIsNone(credentials.load_key())
            credentials.delete_key()
        api.CredDeleteW.assert_called_once_with(credentials._TARGET, 1, 0)

    def test_native_failures_are_sanitized(self):
        api = Mock()
        api.CredReadW.return_value = api.CredWriteW.return_value = api.CredDeleteW.return_value = 0
        with patch.object(credentials, "is_supported", return_value=True), patch.object(credentials, "_api", return_value=api), \
                patch.object(ctypes, "get_last_error", return_value=5):
            for operation in (credentials.load_key, lambda: credentials.save_key(FAKE_KEY), credentials.delete_key):
                with self.assertRaises(credentials.CredentialStoreError) as error:
                    operation()
                self.assertNotIn(FAKE_KEY, str(error.exception))

    def test_invalid_key_does_not_touch_os_store(self):
        with patch.object(credentials, "_api") as api:
            for value in (None, "", "short", "key with spaces is not valid", "x" * 513):
                with self.assertRaises(credentials.CredentialStoreError):
                    credentials.save_key(value)
            api.assert_not_called()

    def test_unsupported_platform_does_not_read_any_store(self):
        with patch.object(credentials, "is_supported", return_value=False), patch.object(credentials, "_api") as api:
            self.assertIsNone(credentials.load_key())
            api.assert_not_called()


if __name__ == "__main__":
    unittest.main()
