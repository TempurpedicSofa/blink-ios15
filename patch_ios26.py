#!/usr/bin/env python3
"""Make a Blink 18.7.0 tree installable with a free Apple ID sideload.

The developer publishing flag is set in developer_setup.xcconfig. This script
only removes entitlements a free profile cannot grant, and keeps SSH config in
the app sandbox when no app-group container exists.
"""

import pathlib
import sys


EMPTY_ENTITLEMENTS = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
</dict>
</plist>
"""


def replace_once(path: pathlib.Path, old: str, new: str, label: str) -> None:
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match in {path}, found {count}")
    path.write_text(text.replace(old, new, 1))
    print(f"patched {label}")


def main() -> None:
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    paths = root / "BlinkConfig" / "BlinkPaths.m"
    delegate = root / "Blink" / "AppDelegate.m"

    replace_once(
        paths,
        """    NSString *path = [fm containerURLForSecurityApplicationGroupIdentifier:groupID].path;
    __groupContainerPath = path;""",
        """    NSString *path = [fm containerURLForSecurityApplicationGroupIdentifier:groupID].path;
    if (path.length == 0) {
      // A free sideload profile has no app group. SSH config stays in the app sandbox.
      path = NSHomeDirectory();
    }
    __groupContainerPath = path;""",
        "group container fallback",
    )

    replace_once(
        paths,
        """    NSString *path = [[fm URLForUbiquityContainerIdentifier:iCloudID] URLByAppendingPathComponent:@"Documents"].path;
    [self _ensureFolderAtPath:path];
    __iCloudsDriveDocumentsPath = path;""",
        """    NSURL *base = [fm URLForUbiquityContainerIdentifier:iCloudID];
    if (base == nil) {
      return nil;
    }
    NSString *path = [base URLByAppendingPathComponent:@"Documents"].path;
    [self _ensureFolderAtPath:path];
    __iCloudsDriveDocumentsPath = path;""",
        "icloud nil guard",
    )

    replace_once(
        paths,
        """+ (void)linkICloudDriveIfNeeded
{
  [self _linkAtPath:[[self homePath] stringByAppendingPathComponent:@"iCloud"]
    destinationPath:[self iCloudDriveDocuments]];
}""",
        """+ (void)linkICloudDriveIfNeeded
{
  NSString *dest = [self iCloudDriveDocuments];
  if (dest.length == 0 || [self homePath].length == 0) {
    return;
  }
  [self _linkAtPath:[[self homePath] stringByAppendingPathComponent:@"iCloud"]
    destinationPath:dest];
}""",
        "skip icloud link",
    )

    replace_once(
        delegate,
        "  [Migrator perform];\n",
        "  // No previous container on a fresh sideload, and Migrator traps without an app group.\n"
        "  // [Migrator perform];\n",
        "skip migrator",
    )

    replace_once(
        delegate,
        "  [_NSFileProviderManager syncWithBKHosts];\n",
        "  // The file-provider extension is omitted from the sideload IPA.\n"
        "  // [_NSFileProviderManager syncWithBKHosts];\n",
        "skip file provider",
    )

    replace_once(
        delegate,
        """  NSString *homePath = BlinkPaths.homePath;
  setenv("HOME", homePath.UTF8String, 1);""",
        """  NSString *homePath = BlinkPaths.homePath;
  if (homePath.length == 0) {
    homePath = NSHomeDirectory();
  }
  setenv("HOME", homePath.UTF8String, 1);""",
        "home path guard",
    )

    written = 0
    for ent in root.rglob("*.entitlements"):
        if "Pods" in ent.parts or ".build" in ent.parts:
            continue
        ent.write_text(EMPTY_ENTITLEMENTS)
        written += 1
        print(f"cleared {ent}")
    if written < 1:
        raise SystemExit("no entitlements files found")


if __name__ == "__main__":
    main()
