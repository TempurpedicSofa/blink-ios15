Build an unsigned Blink Shell 15.0.10 IPA for iPadOS 15.

The workflow checks out blinksh/blink at 838ba6be408f, the last commit whose app target is iOS 15.0, and compiles it on a GitHub-hosted macOS 14 runner with Xcode 15.4. Signing is off so TrollStore can install the IPA.
