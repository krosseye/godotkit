# CHANGELOG

<!-- version list -->

## v0.7.1 (2026-11-07)

### Continuous Integration

- Skip build and publish when no new version is released
  ([`ea4bdcc`](https://github.com/krosseye/godotkit/commit/ea4bdcc004820cc0f080c515c3c20cda31f2effb))

### Performance Improvements

- Reduce GitHub API calls when fetching releases
  ([`6d8a684`](https://github.com/krosseye/godotkit/commit/6d8a684f96f23b2bdc95fa5ee7d44926a1b4e490))


## v0.7.0 (2026-11-06)

### Features

- Support Linux and macOS engine installs
  ([`b8f15d7`](https://github.com/krosseye/godotkit/commit/b8f15d718aa7aabacfdc2f33f2fbad01fc4d6cef))


## v0.6.1 (2026-11-03)

### Bug Fixes

- Apply release filters after caching
  ([`cf57a8f`](https://github.com/krosseye/godotkit/commit/cf57a8fa1c45113229d52493e27dbbe861057e40))

- Keep existing repo until overwrite clone succeeds
  ([`41e37c4`](https://github.com/krosseye/godotkit/commit/41e37c4311665e306f5ed79080f5a6d0d9c763ff))

- Make GodotVersion equality and ordering consistent
  ([`142275b`](https://github.com/krosseye/godotkit/commit/142275bf7286d29208aac8d9b5cdedbe40160d1c))

- Pass paths to file manager without shell quoting
  ([`2fb20be`](https://github.com/krosseye/godotkit/commit/2fb20be9d779f9bd07091efddb299a03365df39c))

- Preserve all config/features entries
  ([`c0e593a`](https://github.com/krosseye/godotkit/commit/c0e593acf6c662c6deca9bcc48d3d7f2a24b882c))

- Prevent overwriting or corrupting project.godot
  ([`519c549`](https://github.com/krosseye/godotkit/commit/519c549da70642141b174290009a499e673bca53))

- Return GodotVersion from major_minor instead of float
  ([`6d5168a`](https://github.com/krosseye/godotkit/commit/6d5168a37be9207fc00e959c726d8d69d46a3adb))

- Stop constants module shadowing its own __name__
  ([`6ed3ae7`](https://github.com/krosseye/godotkit/commit/6ed3ae7966f52ed95b3fc8c584530d988d30863b))


## v0.6.0 (2026-10-31)

### Bug Fixes

- Linter issues
  ([`2f2a15b`](https://github.com/krosseye/godotkit/commit/2f2a15b069f578c34e33fd1b741c254895a0a168))

- Prevent properties from silently dropping non-existent project fields
  ([`1b25377`](https://github.com/krosseye/godotkit/commit/1b253776446ab4068626af89c8c47a7875b56ba0))

- Prevent windows calls being called on linux
  ([`66b2c3e`](https://github.com/krosseye/godotkit/commit/66b2c3e33e597d0c9b0514baf731befea1fa2f03))

### Features

- Drop support for Python 3.9 and update project dependencies
  ([`cc6c651`](https://github.com/krosseye/godotkit/commit/cc6c6510b653b7ae6a8a5103d818f5a483e494c9))

### Refactoring

- Move tag parsing out of GodotFetcher.version_sort_key into
  ([`fe6b26d`](https://github.com/krosseye/godotkit/commit/fe6b26d808484f73e06225f25b98bdeac57d117e))

- Update workflows
  ([`0b1f78a`](https://github.com/krosseye/godotkit/commit/0b1f78a29dfdda4d3bc9e06ab01ab67a90989828))


## v0.5.0 (2026-03-08)


## v0.4.3 (2026-02-18)

### Bug Fixes

- Fix failing 3.9 build
  ([`462a6b7`](https://github.com/krosseye/godotkit/commit/462a6b70e690498325d5bafd83cd6838e7233853))

- Project icon not replacing
  ([`1acba83`](https://github.com/krosseye/godotkit/commit/1acba836c189a8e2d298682422961012748f2124))


## v0.4.2 (2026-02-17)

### Bug Fixes

- Small fixes
  ([`8fe8f69`](https://github.com/krosseye/godotkit/commit/8fe8f6967b32b75e09b1d02f4f19962e64ba3f52))

### Refactoring

- Add icon replacement to update
  ([`08600b9`](https://github.com/krosseye/godotkit/commit/08600b93a872018bdea3e5d6002f6594cbaf084a))


## v0.4.1 (2026-02-17)


## v0.4.0 (2026-02-17)

### Features

- Add project update function
  ([`4daa1df`](https://github.com/krosseye/godotkit/commit/4daa1dfe7b6324d2f62280f83391e3190206def4))

### Refactoring

- Make project write operations atomic
  ([`2a352c8`](https://github.com/krosseye/godotkit/commit/2a352c8cc3f117842cb5ebd59b5c3f3e8821cd0b))


## v0.3.1 (2025-11-13)

### Bug Fixes

- Run engine detached
  ([`633f4ef`](https://github.com/krosseye/godotkit/commit/633f4efe12bb30e5e4ef7870b5ae7dee3dfb9d12))


## v0.3.0 (2025-11-12)

### Features

- Implement RSS feed fetcher
  ([`9ad0d99`](https://github.com/krosseye/godotkit/commit/9ad0d9952391c29473ce76fd038b25fdf4a219c1))


## v0.2.0 (2025-11-12)

### Chores

- Add .gitattributes
  ([`bd1ca92`](https://github.com/krosseye/godotkit/commit/bd1ca92632649c634f46adcc50a89bfa6bc00bb4))

- Implement prek for pre-commit
  ([`7541456`](https://github.com/krosseye/godotkit/commit/75414565f52bf7134662d163e46226c07950b270))

- Remove mixed-line-ending as this is handled by .gitattributes
  ([`c56f29e`](https://github.com/krosseye/godotkit/commit/c56f29e98c8b10a4012a2b26515b9f4868c8abca))

### Documentation

- Include setup instructions
  ([`509f940`](https://github.com/krosseye/godotkit/commit/509f9409de5c8ed3414d620cd67bd0b4773d3c2a))

### Features

- Implement project parsing and utils
  ([`89bd018`](https://github.com/krosseye/godotkit/commit/89bd01805f27c1f45c3c3180f5fd9283de50172c))

### Refactoring

- Generalise functions
  ([`e9ea843`](https://github.com/krosseye/godotkit/commit/e9ea8437bf75ea4030e994ab2a366fb96afdb668))

- Replace print statements with logging
  ([`f74a592`](https://github.com/krosseye/godotkit/commit/f74a592652a023d1efa51e000e6ca9f497587aa1))

### Testing

- Expand test range
  ([`a1fee65`](https://github.com/krosseye/godotkit/commit/a1fee659a1c97074e22910f3d3abe85033615583))

- Run tests from 3.9 to 3.14
  ([`bfd05f6`](https://github.com/krosseye/godotkit/commit/bfd05f66ebc4dd4910e512e433536c7de40edc01))


## v0.1.0 (2025-11-02)

- Initial Release
