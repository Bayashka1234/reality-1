Get-Clipboard | Set-Content "D:\reality-1\capcut_bridge.py" -Encoding UTF8; python "D:\reality-1\capcut_bridge.py"; git -C "D:\reality-1" add capcut_bridge.py; git -C "D:\reality-1" commit -m "Update capcut_bridge.py with SQLite migration"; git -C "D:\reality-1" push

