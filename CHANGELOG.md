# CHANGELOG

<!-- version list -->

## v0.12.0 (2026-11-24)

### Features

- Read releases from godot-builds files and verify downloads
  ([`2587ccf`](https://github.com/krosseye/godotkit/commit/2587ccf1de47c9d26b33490d284a393df621c9c9))


## v0.11.0 (2026-11-22)

### Features

- Launch with captured output
  ([`b3bff1b`](https://github.com/krosseye/godotkit/commit/b3bff1b92a925f1839893be8c657ca4bf94f1f95))

- Let Godot launch failures raise
  ([`9c7f262`](https://github.com/krosseye/godotkit/commit/9c7f262a7c4047944a6651071f10b5c9c0f92240))

- Make common module private
  ([`09815b2`](https://github.com/krosseye/godotkit/commit/09815b28404955de3bbb2ed67a326abfcd38f4f6))

- Make init_repo raise instead of returning bool
  ([`234bf40`](https://github.com/krosseye/godotkit/commit/234bf406436f08ac8e7329acc7f4f1d2388b8d94))

- Remove feed module
  ([`6e52029`](https://github.com/krosseye/godotkit/commit/6e520298c3d65f2dcca63e32c6f60e65b789c7bd))

- Remove trivial wrapper functions
  ([`933e256`](https://github.com/krosseye/godotkit/commit/933e256538255b6f4f827d8cc328eb5e80469c4d))


## v0.10.0 (2026-11-22)

### Bug Fixes

- Reject unknown channels and lossy channel numbers
  ([`b2abb10`](https://github.com/krosseye/godotkit/commit/b2abb1008cb5b1e43e64c53f6d8d9e044074976f))

### Build System

- Bump pydantic to 2.14.4 for Python 3.15 wheels
  ([`173ed37`](https://github.com/krosseye/godotkit/commit/173ed37bd5202b0a4275773d5f677429c1625399))

### Continuous Integration

- Commit uv.lock and install locked dependencies
  ([`732ea0c`](https://github.com/krosseye/godotkit/commit/732ea0c1d12997821e72cc377f87bd04a59f8b60))

### Features

- Cancellable downloads, phase reporting, no silent skip
  ([`e0fec07`](https://github.com/krosseye/godotkit/commit/e0fec07be38cdc5c30c68bbaf2c29e7c28636163))

- Configurable release cache and target filtering
  ([`02b3d1d`](https://github.com/krosseye/godotkit/commit/02b3d1d5d866a94041005f5474f5c5c2a7c5fee2))

- Dotted canonical version format
  ([`e703dab`](https://github.com/krosseye/godotkit/commit/e703dabf90b75c5c5386e102785d5b734a3ebe84))

- GodotRelease.version is a GodotVersion
  ([`316b208`](https://github.com/krosseye/godotkit/commit/316b208c6200c81be02a8d1bc6751ea3257ca8c3))

- Look up releases by GodotVersion
  ([`34d706b`](https://github.com/krosseye/godotkit/commit/34d706b47adf3cf321f9c3406e2baa090401a8c4))

- Public GodotProject.update(metadata)
  ([`484df38`](https://github.com/krosseye/godotkit/commit/484df3886bddb1463cf53f4227e356cc1dfd665b))

- Return None for missing project metadata
  ([`98e7007`](https://github.com/krosseye/godotkit/commit/98e7007fc9e7b36a1dd75e96b3bbd51d0d689e71))


## v0.9.0 (2026-11-20)

### Bug Fixes

- Use one release source with correct dates
  ([`e64ed57`](https://github.com/krosseye/godotkit/commit/e64ed576b9aeabe9aa64aa8e271c33024593b955))

### Features

- Add GodotkitError base exception
  ([`b8e20e2`](https://github.com/krosseye/godotkit/commit/b8e20e255bbf7b6f61b135a80c101b3609449df0))

- Add GodotVersion.to_tag()
  ([`d37ff5f`](https://github.com/krosseye/godotkit/commit/d37ff5f5acadb0909104ae3bcca76d4b4f795354))

- Make GodotVersion immutable
  ([`fee7400`](https://github.com/krosseye/godotkit/commit/fee740074cc3bdd1dc19a47add9357d88f048186))


## v0.8.1 (2026-11-19)

### Bug Fixes

- Raise ExtractError for an empty zip
  ([`fca85b9`](https://github.com/krosseye/godotkit/commit/fca85b9c8abdf9186dc7a05beeab0062627cd235))

### Continuous Integration

- Publish releases to PyPI
  ([`b6873ba`](https://github.com/krosseye/godotkit/commit/b6873baf59dece6249ba72af5c91eb70c7c54d41))


## v0.8.0 (2026-11-18)

### Bug Fixes

- Extract downloads atomically
  ([`02a4bb7`](https://github.com/krosseye/godotkit/commit/02a4bb77f9ffaa1e5358a439e8a653eb4d720359))

- Report unknown version as 0.0.0
  ([`1c59faf`](https://github.com/krosseye/godotkit/commit/1c59faf266eec4a063abdc7e461bf2f4d3b82316))

- Use the platform cache dir on macOS
  ([`978db18`](https://github.com/krosseye/godotkit/commit/978db18c9cbeb6d8f0778f2cc47eecb64884de5e))

### Features

- Add close() to the HTTP fetchers
  ([`719b1c8`](https://github.com/krosseye/godotkit/commit/719b1c8b1955257f1b0145705c7cbb17fb240137))

### Refactoring

- Use lazy % formatting in log calls
  ([`daf4a2c`](https://github.com/krosseye/godotkit/commit/daf4a2c4a8afa1c6d643e36a2fea54ff8c14d68a))

### Testing

- Cover install restore when the swap fails
  ([`a051583`](https://github.com/krosseye/godotkit/commit/a051583475f9ef25706f248cd768c86fd0711872))


## v0.7.2 (2026-11-16)

### Bug Fixes

- Match release assets by exact filename
  ([`e0865e3`](https://github.com/krosseye/godotkit/commit/e0865e3766727cd7392ee3eb9d3f9a28247909d1))

- Preserve line endings when writing project files
  ([`c396d3a`](https://github.com/krosseye/godotkit/commit/c396d3af21bd614ab31783bcbba32acb3863cd02))

### Chores

- **deps-dev**: Update uv-build requirement
  ([`3c7efb1`](https://github.com/krosseye/godotkit/commit/3c7efb10afe15b03d82f3ca2b77c35da227bc409))

### Continuous Integration

- Bump actions/checkout from 5 to 7
  ([`7bc8f5a`](https://github.com/krosseye/godotkit/commit/7bc8f5a639915bccdc2c95b2d31b93da9a8bd7f6))

- Bump actions/deploy-pages from 4 to 5
  ([`c9162b0`](https://github.com/krosseye/godotkit/commit/c9162b0d5a6adde17130eacb83859f2ad92f262a))

- Bump actions/setup-python from 6 to 7
  ([`b9a1ab7`](https://github.com/krosseye/godotkit/commit/b9a1ab74d589f4390f6e6ee2e0aac0fcce3f8a2d))

- Bump actions/upload-pages-artifact from 4 to 5
  ([`5173839`](https://github.com/krosseye/godotkit/commit/5173839b60e33d3bd9238f050a45b60b50bd9aef))

- Bump astral-sh/setup-uv from 6 to 7
  ([`801d902`](https://github.com/krosseye/godotkit/commit/801d9026b5cf3266ec24c3f0da002474826ea88c))

- Skip tests and release on docs only pushes
  ([`ea90c8d`](https://github.com/krosseye/godotkit/commit/ea90c8d094e651c0c88546e188900a03c6a9b18c))

- Test on windows and macos
  ([`6658bfd`](https://github.com/krosseye/godotkit/commit/6658bfdd4c3ace3018fb615df701803c4d6cbe12))

- Tweak workflow timings
  ([`8ff716c`](https://github.com/krosseye/godotkit/commit/8ff716c391b1bb1db79e01521db1508413cc9571))

- Weekly check against godot-builds releases
  ([`52693cb`](https://github.com/krosseye/godotkit/commit/52693cb878c1693da79746b22f1f3e93af6c73a8))

### Documentation

- Update badges in README and docs
  ([`4eb4ed2`](https://github.com/krosseye/godotkit/commit/4eb4ed2d16fc4a6d06ff3dfcb46169377aa6bcb6))

### Testing

- Run platform detection and process launch on the native OS
  ([`5f6e816`](https://github.com/krosseye/godotkit/commit/5f6e81604f6c36baebe96f31e501757abe4a8f9f))


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
