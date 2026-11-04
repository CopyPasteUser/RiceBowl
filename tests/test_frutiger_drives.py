"""Gio-backed Aqua mounts never touch system roots or force-unmount devices."""

import unittest
from types import SimpleNamespace
from unittest import mock

from macrice.frutiger_drives import AquaDrives, visible_mounts


def mount(name, uri, *, shadowed=False, unmount=True):
    item = mock.Mock()
    item.get_name.return_value = name
    item.is_shadowed.return_value = shadowed
    item.get_default_location.return_value.get_uri.return_value = uri
    item.can_unmount.return_value = unmount
    item.unmount_with_operation_finish.return_value = True
    return item


class DriveTests(unittest.TestCase):
    def test_shadows_internal_roots_and_expansion_are_filtered(self):
        removable = mount("USB Stick", "file:///media/usb")
        rows = visible_mounts([mount("Root", "file:///"), removable,
                               mount("EFI", "file:///boot/efi"),
                               mount("System", "file:///proc/sys"),
                               mount("Hidden", "sftp://hidden", shadowed=True),
                               mount("Network", "smb://server/share")])
        self.assertEqual([(name, uri) for name, uri, _item in rows],
                         [("Network", "smb://server/share"), ("USB Stick", "file:///media/usb")])
        self.assertIs(rows[1][2], removable)

    def _panel(self, response):
        instance = AquaDrives.__new__(AquaDrives)
        dialog = mock.Mock()
        dialog.run.return_value = response
        gtk = SimpleNamespace(
            MessageDialog=mock.Mock(return_value=dialog),
            MessageType=SimpleNamespace(QUESTION=0),
            ButtonsType=SimpleNamespace(NONE=0),
            ResponseType=SimpleNamespace(CANCEL=1, OK=2),
            MountOperation=SimpleNamespace(new=lambda _parent: object()),
        )
        instance.Gtk = gtk
        instance.Gio = SimpleNamespace(MountUnmountFlags=SimpleNamespace(NONE=0))
        instance.shell = SimpleNamespace(bar=mock.Mock())
        instance.status = mock.Mock()
        instance.popover = mock.Mock()
        instance.popover.get_visible.return_value = True
        instance.refresh = mock.Mock()
        instance.pending = False
        instance._closed = False
        return instance, dialog

    def test_user_must_confirm_before_safe_unmount_is_requested(self):
        panel, dialog = self._panel(response=1)
        item = mount("USB", "file:///media/usb")
        panel._confirm_unmount(item, "USB")
        item.unmount_with_operation.assert_not_called()
        self.assertFalse(panel.pending)
        dialog.destroy.assert_called_once()

    def test_confirmed_unmount_is_async_and_finished_before_success(self):
        panel, dialog = self._panel(response=2)
        item = mount("USB", "file:///media/usb")
        panel._confirm_unmount(item, "USB")
        self.assertTrue(panel.pending)
        callback = item.unmount_with_operation.call_args.args[3]
        callback(item, object())
        item.unmount_with_operation_finish.assert_called_once()
        self.assertFalse(panel.pending)
        panel.status.set_text.assert_any_call("Unmount complete")
        panel.refresh.assert_called_once()

    def test_unmount_failure_is_reported_without_force_or_retry(self):
        panel, _dialog = self._panel(response=2)
        item = mount("USB", "file:///media/usb")
        item.unmount_with_operation_finish.side_effect = RuntimeError("Device busy")
        panel._confirm_unmount(item, "USB")
        callback = item.unmount_with_operation.call_args.args[3]
        callback(item, object())
        self.assertFalse(panel.pending)
        self.assertTrue(any("Device busy" in call.args[0]
                            for call in panel.status.set_text.call_args_list))
        self.assertEqual(item.unmount_with_operation.call_count, 1)

    def test_device_disappearing_before_confirmation_is_safe(self):
        panel, _dialog = self._panel(response=2)
        item = mount("USB", "file:///media/usb")
        item.can_unmount.side_effect = RuntimeError("Gone")
        panel._confirm_unmount(item, "USB")
        item.unmount_with_operation.assert_not_called()
        panel.status.set_text.assert_called_once_with("The location is no longer available")

    def test_async_unmount_after_popup_shutdown_does_not_render(self):
        panel, _dialog = self._panel(response=2)
        item = mount("USB", "file:///media/usb")
        panel._confirm_unmount(item, "USB")
        panel._closed = True
        callback = item.unmount_with_operation.call_args.args[3]
        callback(item, object())
        self.assertFalse(panel.pending)
        panel.refresh.assert_not_called()


if __name__ == "__main__":
    unittest.main()
