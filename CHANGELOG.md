# CHANGELOG

<!-- version list -->

## v2.3.0 (2026-06-22)

### Bug Fixes

- Drop out-of-range CO2 readings from Meter Pro CO2
  ([#491](https://github.com/sblibs/pySwitchbot/pull/491),
  [`9aa5f50`](https://github.com/sblibs/pySwitchbot/commit/9aa5f50e8620bd37ad6a799eff8c5ec3aa4faa38))

- Guard leak, presence_sensor, contact parsers against short mfr_data
  ([#495](https://github.com/sblibs/pySwitchbot/pull/495),
  [`226b170`](https://github.com/sblibs/pySwitchbot/commit/226b170b70c0e823d1a3f14335f74ece136ee2b5))

- Guard relay_switch get_basic_info against short responses
  ([#509](https://github.com/sblibs/pySwitchbot/pull/509),
  [`7b7b8f1`](https://github.com/sblibs/pySwitchbot/commit/7b7b8f1cac8bb325f8db2b776f51668c4d276c6a))

- Guard remaining adv_parsers against short payloads
  ([#496](https://github.com/sblibs/pySwitchbot/pull/496),
  [`ac01f2c`](https://github.com/sblibs/pySwitchbot/commit/ac01f2cd1f29e3d1780af223d0961b77802cd443))

- Infer TRV idle state when target temperature is reached with 0.5°C hysteresis
  ([#521](https://github.com/sblibs/pySwitchbot/pull/521),
  [`c1d7775`](https://github.com/sblibs/pySwitchbot/commit/c1d77759f931f4b571bf4981851acf6e1f16c163))

- Leak detector with passive scanning ([#512](https://github.com/sblibs/pySwitchbot/pull/512),
  [`81291fe`](https://github.com/sblibs/pySwitchbot/commit/81291fe7bcbe1f4421b6b792c60c970bcd0abc65))

- Silence spurious _update_parsed_data log noise (#285)
  ([#493](https://github.com/sblibs/pySwitchbot/pull/493),
  [`ece305a`](https://github.com/sblibs/pySwitchbot/commit/ece305af0fca512ca395a4cfc06e369d8d66e804))

### Chores

- Enable additional ruff lint rules ([#524](https://github.com/sblibs/pySwitchbot/pull/524),
  [`c454711`](https://github.com/sblibs/pySwitchbot/commit/c45471152eb03bea023336642d0f81be19ba2052))

- **ci**: Bump codecov/codecov-action from 6.0.0 to 6.0.1 in the github-actions group
  ([#511](https://github.com/sblibs/pySwitchbot/pull/511),
  [`f08a9c1`](https://github.com/sblibs/pySwitchbot/commit/f08a9c157255fb71f051149b7dd89da610040bc1))

- **deps**: Update aiohttp requirement from >=3.13.5 to >=3.14.1
  ([#514](https://github.com/sblibs/pySwitchbot/pull/514),
  [`86b3952`](https://github.com/sblibs/pySwitchbot/commit/86b39523f2f767b04e0269d09f5f2d22d2fda69a))

- **deps**: Update aiohttp requirement from >=3.9.5 to >=3.13.5
  ([#481](https://github.com/sblibs/pySwitchbot/pull/481),
  [`bada155`](https://github.com/sblibs/pySwitchbot/commit/bada155529b92da9e7e9669314019f44acc04c0d))

- **deps**: Update bleak requirement from >=0.17.0 to >=3.0.2
  ([#486](https://github.com/sblibs/pySwitchbot/pull/486),
  [`6029aae`](https://github.com/sblibs/pySwitchbot/commit/6029aae49ad4a92df4c85b4c594b071884385315))

- **deps**: Update bleak-retry-connector requirement from >=2.9.0 to >=4.6.0
  ([#484](https://github.com/sblibs/pySwitchbot/pull/484),
  [`59e2dec`](https://github.com/sblibs/pySwitchbot/commit/59e2dec045e0680d8895faa60cfa2eb8798172c9))

- **deps**: Update bleak-retry-connector requirement from >=4.6.0 to >=4.6.1
  ([#505](https://github.com/sblibs/pySwitchbot/pull/505),
  [`e60f634`](https://github.com/sblibs/pySwitchbot/commit/e60f63475cc5fd290bf0f469568ff8afc7af6172))

- **deps**: Update cryptography requirement from >=38.0.3 to >=47.0.0
  ([#482](https://github.com/sblibs/pySwitchbot/pull/482),
  [`4e40fcc`](https://github.com/sblibs/pySwitchbot/commit/4e40fcc5d3307941764f64df9d57e58f9a24f3cd))

- **deps**: Update cryptography requirement from >=47.0.0 to >=48.0.0
  ([#487](https://github.com/sblibs/pySwitchbot/pull/487),
  [`1bcde50`](https://github.com/sblibs/pySwitchbot/commit/1bcde50227d5acabaa1df180de6937b30b5d1d28))

- **deps**: Update cryptography requirement from >=48.0.0 to >=49.0.0
  ([#519](https://github.com/sblibs/pySwitchbot/pull/519),
  [`cdcf5e8`](https://github.com/sblibs/pySwitchbot/commit/cdcf5e88be53723f6a0715e4644ce74203176b0b))

- **pre-commit.ci**: Pre-commit autoupdate ([#513](https://github.com/sblibs/pySwitchbot/pull/513),
  [`6ecbc09`](https://github.com/sblibs/pySwitchbot/commit/6ecbc09a775166585a96d04b605311251f76bb9a))

- **pre-commit.ci**: Pre-commit autoupdate ([#504](https://github.com/sblibs/pySwitchbot/pull/504),
  [`0d02e37`](https://github.com/sblibs/pySwitchbot/commit/0d02e3783dd65ce126003d03c351cad5d91693a4))

- **pre-commit.ci**: Pre-commit autoupdate ([#501](https://github.com/sblibs/pySwitchbot/pull/501),
  [`9831b51`](https://github.com/sblibs/pySwitchbot/commit/9831b517b0f9fa6cd24b110656e04ac8d204c780))

- **pre-commit.ci**: Pre-commit autoupdate ([#485](https://github.com/sblibs/pySwitchbot/pull/485),
  [`e036cd1`](https://github.com/sblibs/pySwitchbot/commit/e036cd1d26bf89c577fe58267577f489a5eef538))

- **pre-commit.ci**: Pre-commit autoupdate ([#480](https://github.com/sblibs/pySwitchbot/pull/480),
  [`f4e8290`](https://github.com/sblibs/pySwitchbot/commit/f4e82903e2bfc51e046a0221894a3bf218c020c6))

### Continuous Integration

- Migrate to poetry and python-semantic-release releases
  ([#527](https://github.com/sblibs/pySwitchbot/pull/527),
  [`d3b20e4`](https://github.com/sblibs/pySwitchbot/commit/d3b20e40d9eeb324ce5d1c549b32ff59fad6aef6))

- Use release-bot App token so PSR can push past branch protection
  ([#528](https://github.com/sblibs/pySwitchbot/pull/528),
  [`0d193d8`](https://github.com/sblibs/pySwitchbot/commit/0d193d8ae4da65fa0d614deb261374316675cd09))

### Documentation

- Add AGENTS.md for contributors ([#523](https://github.com/sblibs/pySwitchbot/pull/523),
  [`511314b`](https://github.com/sblibs/pySwitchbot/commit/511314b07d113be83ab0d7b3d8c832e1a03cc46e))

- Document common key-retrieval failure modes
  ([#525](https://github.com/sblibs/pySwitchbot/pull/525),
  [`fe8c46c`](https://github.com/sblibs/pySwitchbot/commit/fe8c46c87a8354ff33140230d6a0f1d4a7e1daa7))

- Fix undefined ENCRYPTION_KEY in README lock examples
  ([#516](https://github.com/sblibs/pySwitchbot/pull/516),
  [`2ebdb48`](https://github.com/sblibs/pySwitchbot/commit/2ebdb48ed3c8557e5efb62436a9c096b863fb719))

### Features

- Add RGBICWW Ceiling Light support ([#507](https://github.com/sblibs/pySwitchbot/pull/507),
  [`0a59efd`](https://github.com/sblibs/pySwitchbot/commit/0a59efdd5976169f3638e5e059ea5d2704ad46f3))


## v2.2.0 (2026-04-24)

### Continuous Integration

- Auto-close PRs opened from a fork's default branch
  ([#477](https://github.com/sblibs/pySwitchbot/pull/477),
  [`c4227f9`](https://github.com/sblibs/pySwitchbot/commit/c4227f96b8052e4465772bf8e7c82c9345165dc8))

### Refactoring

- Replace model-default override boilerplate with `_model` classvar
  ([#476](https://github.com/sblibs/pySwitchbot/pull/476),
  [`e75f8c7`](https://github.com/sblibs/pySwitchbot/commit/e75f8c71ca6bdfe6bf763a61abfd70fa18e6d0b0))


## v2.1.0 (2026-04-21)

### Chores

- **pre-commit.ci**: Pre-commit autoupdate ([#473](https://github.com/sblibs/pySwitchbot/pull/473),
  [`978b47b`](https://github.com/sblibs/pySwitchbot/commit/978b47bff8e1f9e411e7d28b4449aaabaecb5567))

- **pre-commit.ci**: Pre-commit autoupdate ([#471](https://github.com/sblibs/pySwitchbot/pull/471),
  [`467f8f9`](https://github.com/sblibs/pySwitchbot/commit/467f8f9339a33795ac9a00974897308e8fc5d4e5))


## v2.0.1 (2026-04-12)

### Chores

- **ci**: Bump codecov/codecov-action from 5.5.2 to 6.0.0 in the github-actions group
  ([#467](https://github.com/sblibs/pySwitchbot/pull/467),
  [`ddeac1a`](https://github.com/sblibs/pySwitchbot/commit/ddeac1afb7991b291732f8554167cad96f07c2e2))

- **pre-commit.ci**: Pre-commit autoupdate ([#466](https://github.com/sblibs/pySwitchbot/pull/466),
  [`258c1c5`](https://github.com/sblibs/pySwitchbot/commit/258c1c50103825fb7519c3ca2899f00112e25a01))

- **pre-commit.ci**: Pre-commit autoupdate ([#465](https://github.com/sblibs/pySwitchbot/pull/465),
  [`0547599`](https://github.com/sblibs/pySwitchbot/commit/05475999701e5fd6ed877cd7235ee4ff76a16026))


## v2.0.0 (2026-03-13)

### Chores

- **ci**: Bump the github-actions group with 2 updates
  ([#453](https://github.com/sblibs/pySwitchbot/pull/453),
  [`b7328e2`](https://github.com/sblibs/pySwitchbot/commit/b7328e2411ee1396bfed0f1a80548bd98f33f2b9))

- **pre-commit.ci**: Pre-commit autoupdate ([#455](https://github.com/sblibs/pySwitchbot/pull/455),
  [`41bf5a6`](https://github.com/sblibs/pySwitchbot/commit/41bf5a67655a478ff8bac66861381f64db36ea79))


## v1.1.0 (2026-02-26)

### Chores

- **pre-commit.ci**: Pre-commit autoupdate ([#446](https://github.com/sblibs/pySwitchbot/pull/446),
  [`bdde342`](https://github.com/sblibs/pySwitchbot/commit/bdde342692241554adc83c95b2dee4986aa32606))


## v1.0.0 (2026-01-25)

### Chores

- **pre-commit.ci**: Pre-commit autoupdate ([#441](https://github.com/sblibs/pySwitchbot/pull/441),
  [`87a99ad`](https://github.com/sblibs/pySwitchbot/commit/87a99ad4faabd065810358324efeff885e7e94a9))

- **pre-commit.ci**: Pre-commit autoupdate ([#440](https://github.com/sblibs/pySwitchbot/pull/440),
  [`1c78975`](https://github.com/sblibs/pySwitchbot/commit/1c789752eb76e0419cb30d2e407b8efe75ae173e))

### Features

- **discovery**: Add callback support for device discovery
  ([#437](https://github.com/sblibs/pySwitchbot/pull/437),
  [`dbbe591`](https://github.com/sblibs/pySwitchbot/commit/dbbe591269041a8062e21cfc729b4be7e25fed9a))


## v0.76.0 (2026-01-07)

### Chores

- **ci**: Bump the github-actions group with 3 updates
  ([#434](https://github.com/sblibs/pySwitchbot/pull/434),
  [`b21f99d`](https://github.com/sblibs/pySwitchbot/commit/b21f99d1b8ff4bd35ab4dca3f0c9fde4adb5a0bb))

- **pre-commit.ci**: Pre-commit autoupdate ([#435](https://github.com/sblibs/pySwitchbot/pull/435),
  [`1224dff`](https://github.com/sblibs/pySwitchbot/commit/1224dff4634a3e0fa1f84b2fac17f187772c01ca))

- **pre-commit.ci**: Pre-commit autoupdate ([#432](https://github.com/sblibs/pySwitchbot/pull/432),
  [`511a0d2`](https://github.com/sblibs/pySwitchbot/commit/511a0d2e29e87ae9d14f7f2345add571c66b2e5d))


## v0.75.0 (2025-12-23)

### Chores

- **ci**: Bump actions/checkout from 5 to 6 in the github-actions group
  ([#423](https://github.com/sblibs/pySwitchbot/pull/423),
  [`92278f8`](https://github.com/sblibs/pySwitchbot/commit/92278f8a040bdbb4f10447af1c6e1628a3fda052))

- **pre-commit.ci**: Pre-commit autoupdate ([#427](https://github.com/sblibs/pySwitchbot/pull/427),
  [`19ce9ac`](https://github.com/sblibs/pySwitchbot/commit/19ce9ac8e986e874ac2e96e9b7c089987baee3aa))

- **pre-commit.ci**: Pre-commit autoupdate ([#422](https://github.com/sblibs/pySwitchbot/pull/422),
  [`7704660`](https://github.com/sblibs/pySwitchbot/commit/77046606a6541ff35c05a92c8ef43a6a1a74fe75))

- **pre-commit.ci**: Pre-commit autoupdate ([#420](https://github.com/sblibs/pySwitchbot/pull/420),
  [`a598326`](https://github.com/sblibs/pySwitchbot/commit/a598326c02b734d6ef37cf11daa8dc69ea2e11fa))

### Features

- **presence sensor**: Add duration parsing and fix lightLevel mask
  ([#426](https://github.com/sblibs/pySwitchbot/pull/426),
  [`eb25905`](https://github.com/sblibs/pySwitchbot/commit/eb2590573595f261b0502b3476b52ca963baae93))


## v0.74.0 (2025-11-21)

### Chores

- **pre-commit.ci**: Pre-commit autoupdate ([#417](https://github.com/sblibs/pySwitchbot/pull/417),
  [`2f2dd6c`](https://github.com/sblibs/pySwitchbot/commit/2f2dd6c90372ac1b3c1bba5026b9203631cbf2ca))

- **pre-commit.ci**: Pre-commit autoupdate ([#414](https://github.com/sblibs/pySwitchbot/pull/414),
  [`b509f03`](https://github.com/sblibs/pySwitchbot/commit/b509f03c8fcef9562cb9dfdf1e3dff18419d82fb))


## v0.73.0 (2025-11-10)

### Chores

- **ci**: Bump the github-actions group with 2 updates
  ([#408](https://github.com/sblibs/pySwitchbot/pull/408),
  [`b414b90`](https://github.com/sblibs/pySwitchbot/commit/b414b90383ffb35100e8eba149996c4e3f1bd467))

- **pre-commit.ci**: Pre-commit autoupdate ([#407](https://github.com/sblibs/pySwitchbot/pull/407),
  [`ce4d698`](https://github.com/sblibs/pySwitchbot/commit/ce4d698faf3055ee5f0f78aa8bdb3ace4871502a))


## v0.72.1 (2025-10-27)


## v0.72.0 (2025-10-23)

### Chores

- **ci**: Bump the github-actions group with 2 updates
  ([#401](https://github.com/sblibs/pySwitchbot/pull/401),
  [`fa7d072`](https://github.com/sblibs/pySwitchbot/commit/fa7d0727d07c3d5a233d97234dc1c654775136ae))

- **pre-commit.ci**: Pre-commit autoupdate ([#400](https://github.com/sblibs/pySwitchbot/pull/400),
  [`2c5be78`](https://github.com/sblibs/pySwitchbot/commit/2c5be78cd61f2911ecb3e490675c2ab25f9a7ebb))


## v0.71.0 (2025-09-18)

### Chores

- **pre-commit.ci**: Pre-commit autoupdate ([#398](https://github.com/sblibs/pySwitchbot/pull/398),
  [`2ec7aab`](https://github.com/sblibs/pySwitchbot/commit/2ec7aab75d36ab11ed3bc5d0675c04a9134ac422))


## v0.70.0 (2025-09-10)

### Chores

- **ci**: Bump the github-actions group with 3 updates
  ([#395](https://github.com/sblibs/pySwitchbot/pull/395),
  [`2201c90`](https://github.com/sblibs/pySwitchbot/commit/2201c9014a6ded7200c70eea488202fb26b64689))

- **pre-commit.ci**: Pre-commit autoupdate ([#394](https://github.com/sblibs/pySwitchbot/pull/394),
  [`6dcc62a`](https://github.com/sblibs/pySwitchbot/commit/6dcc62ac6036720b52af567c0c60123ce7b7e0ac))

- **pre-commit.ci**: Pre-commit autoupdate ([#393](https://github.com/sblibs/pySwitchbot/pull/393),
  [`ec69621`](https://github.com/sblibs/pySwitchbot/commit/ec69621b664f382b2bbf3f015dd78dcf23c0ff43))


## v0.69.0 (2025-08-23)

### Chores

- **pre-commit.ci**: Pre-commit autoupdate ([#388](https://github.com/sblibs/pySwitchbot/pull/388),
  [`2f4e050`](https://github.com/sblibs/pySwitchbot/commit/2f4e0509c0a9fef441c3fb01f088397087c3acad))


## v0.68.4 (2025-08-18)

### Chores

- **pre-commit.ci**: Pre-commit autoupdate ([#383](https://github.com/sblibs/pySwitchbot/pull/383),
  [`304bb9e`](https://github.com/sblibs/pySwitchbot/commit/304bb9ebada0521054eb9a4fbd044029e525e9b1))


## v0.68.3 (2025-08-05)

### Bug Fixes

- Add power adv parser for 1pm ([#380](https://github.com/sblibs/pySwitchbot/pull/380),
  [`645ff8f`](https://github.com/sblibs/pySwitchbot/commit/645ff8f65ff6f3d72fdc8fae1fc9584ea66c6a5c))

### Chores

- **pre-commit.ci**: Pre-commit autoupdate ([#379](https://github.com/sblibs/pySwitchbot/pull/379),
  [`b9e9593`](https://github.com/sblibs/pySwitchbot/commit/b9e9593fdad7b0527febbdffd78de3ea336c5b2c))

- **pre-commit.ci**: Pre-commit autoupdate ([#377](https://github.com/sblibs/pySwitchbot/pull/377),
  [`14100b5`](https://github.com/sblibs/pySwitchbot/commit/14100b526f8e0a6b067970f98ffe5fa5f16031a7))


## v0.68.2 (2025-07-17)

### Chores

- **pre-commit.ci**: Pre-commit autoupdate ([#374](https://github.com/sblibs/pySwitchbot/pull/374),
  [`472eb22`](https://github.com/sblibs/pySwitchbot/commit/472eb2209e263586fb8a502bb59fdcf92d836ce9))

- **pre-commit.ci**: Pre-commit autoupdate ([#371](https://github.com/sblibs/pySwitchbot/pull/371),
  [`3b369fe`](https://github.com/sblibs/pySwitchbot/commit/3b369fe127bd9936d1a9972890bef3f94f98acce))


## v0.68.1 (2025-07-07)


## v0.68.0 (2025-07-03)

### Chores

- **pre-commit.ci**: Pre-commit autoupdate ([#364](https://github.com/sblibs/pySwitchbot/pull/364),
  [`2fb9a18`](https://github.com/sblibs/pySwitchbot/commit/2fb9a18a162b6180862bafa75246ee8ce834c844))


## v0.67.0 (2025-06-25)

### Chores

- **pre-commit.ci**: Pre-commit autoupdate ([#361](https://github.com/sblibs/pySwitchbot/pull/361),
  [`1b14eb3`](https://github.com/sblibs/pySwitchbot/commit/1b14eb3e1b0792f52edbf8bcff64dbfa84c49607))

- **pre-commit.ci**: Pre-commit autoupdate ([#358](https://github.com/sblibs/pySwitchbot/pull/358),
  [`f6463f1`](https://github.com/sblibs/pySwitchbot/commit/f6463f1d6bd9693b319b8f7463ecb860a9f704f5))


## v0.66.0 (2025-06-09)

### Chores

- **pre-commit.ci**: Pre-commit autoupdate ([#351](https://github.com/sblibs/pySwitchbot/pull/351),
  [`2922bbd`](https://github.com/sblibs/pySwitchbot/commit/2922bbd63fac37926532269d439cef2f09695de6))


## v0.65.0 (2025-06-02)

### Chores

- **ci**: Bump codecov/codecov-action from 5.4.2 to 5.4.3 in the github-actions group
  ([#349](https://github.com/sblibs/pySwitchbot/pull/349),
  [`075ba18`](https://github.com/sblibs/pySwitchbot/commit/075ba184654b1d83e4e162463e11b0976390ae36))

- **pre-commit.ci**: Pre-commit autoupdate ([#344](https://github.com/sblibs/pySwitchbot/pull/344),
  [`59fb967`](https://github.com/sblibs/pySwitchbot/commit/59fb967fa0a6fa01761ad4047d0f47bcfe867e48))


## v0.64.1 (2025-05-21)


## v0.64.0 (2025-05-20)

### Chores

- **pre-commit.ci**: Pre-commit autoupdate ([#339](https://github.com/sblibs/pySwitchbot/pull/339),
  [`eda622b`](https://github.com/sblibs/pySwitchbot/commit/eda622b9ce99e3a3b3b764c9082854ef127e8848))


## v0.63.0 (2025-05-19)


## v0.62.2 (2025-05-15)


## v0.62.1 (2025-05-12)

### Chores

- **pre-commit.ci**: Pre-commit autoupdate ([#332](https://github.com/sblibs/pySwitchbot/pull/332),
  [`23ab4ee`](https://github.com/sblibs/pySwitchbot/commit/23ab4ee8e122e8fb390ab4b7fcbd8a4625e872fe))


## v0.62.0 (2025-05-08)


## v0.61.0 (2025-05-07)

### Chores

- **ci**: Bump codecov/codecov-action from 5.4.0 to 5.4.2 in the github-actions group
  ([#324](https://github.com/sblibs/pySwitchbot/pull/324),
  [`95e4054`](https://github.com/sblibs/pySwitchbot/commit/95e4054c0c098d89120076671fac252d67230068))

- **pre-commit.ci**: Pre-commit autoupdate ([#325](https://github.com/sblibs/pySwitchbot/pull/325),
  [`e98909b`](https://github.com/sblibs/pySwitchbot/commit/e98909b0e5beeeac497f60128aed1e292a02cc27))

- **pre-commit.ci**: Pre-commit autoupdate ([#323](https://github.com/sblibs/pySwitchbot/pull/323),
  [`09326d4`](https://github.com/sblibs/pySwitchbot/commit/09326d4a237e2f86219d8c839a83c15d731c5741))


## v0.60.1 (2025-04-23)

### Chores

- **pre-commit.ci**: Pre-commit autoupdate ([#320](https://github.com/sblibs/pySwitchbot/pull/320),
  [`ba0cfee`](https://github.com/sblibs/pySwitchbot/commit/ba0cfeebc4a1b002ec64b60f9280f4fc825016b0))

- **pre-commit.ci**: Pre-commit autoupdate ([#319](https://github.com/sblibs/pySwitchbot/pull/319),
  [`7826d11`](https://github.com/sblibs/pySwitchbot/commit/7826d116a24c03c1b815480e4411ff23f1df0322))


## v0.60.0 (2025-04-13)

### Chores

- **pre-commit.ci**: Pre-commit autoupdate ([#316](https://github.com/sblibs/pySwitchbot/pull/316),
  [`258c5f0`](https://github.com/sblibs/pySwitchbot/commit/258c5f05eced0605c905bc88e324bdce4923f1aa))


## v0.59.0 (2025-04-02)

### Chores

- **pre-commit.ci**: Auto fixes
  ([`a9fa9d6`](https://github.com/sblibs/pySwitchbot/commit/a9fa9d6a0b9ebbc70d5becc029d5c393a2c1ac6b))

- **pre-commit.ci**: Auto fixes
  ([`837c3f3`](https://github.com/sblibs/pySwitchbot/commit/837c3f3134583590ba5a9bd0d412eab7718da3f7))


## v0.58.0 (2025-03-24)

### Bug Fixes

- Light intensity calculation and update tests
  ([#290](https://github.com/sblibs/pySwitchbot/pull/290),
  [`98c1311`](https://github.com/sblibs/pySwitchbot/commit/98c1311512a61f6334230ac2a51f9d6aeba2d751))

### Chores

- **pre-commit.ci**: Pre-commit autoupdate ([#314](https://github.com/sblibs/pySwitchbot/pull/314),
  [`6e977fd`](https://github.com/sblibs/pySwitchbot/commit/6e977fde6b83d45059ad9d9effe7049fed2634df))

- **pre-commit.ci**: Pre-commit autoupdate ([#310](https://github.com/sblibs/pySwitchbot/pull/310),
  [`068cad6`](https://github.com/sblibs/pySwitchbot/commit/068cad676f1fb5db5967bd03a5ff6e1d83ee194c))

### Documentation

- Add docstring for light intensity mapping in hub2.py
  ([#290](https://github.com/sblibs/pySwitchbot/pull/290),
  [`98c1311`](https://github.com/sblibs/pySwitchbot/commit/98c1311512a61f6334230ac2a51f9d6aeba2d751))

### Features

- Calculate hub2 light intensity ([#290](https://github.com/sblibs/pySwitchbot/pull/290),
  [`98c1311`](https://github.com/sblibs/pySwitchbot/commit/98c1311512a61f6334230ac2a51f9d6aeba2d751))

- Refactor light intensity calculation using a constant map
  ([#290](https://github.com/sblibs/pySwitchbot/pull/290),
  [`98c1311`](https://github.com/sblibs/pySwitchbot/commit/98c1311512a61f6334230ac2a51f9d6aeba2d751))


## v0.57.1 (2025-03-15)

### Chores

- **ci**: Bump codecov/codecov-action from 5.3.1 to 5.4.0 in the github-actions group
  ([#307](https://github.com/sblibs/pySwitchbot/pull/307),
  [`e11bce8`](https://github.com/sblibs/pySwitchbot/commit/e11bce8b91c3566ea293037a1d4441e95bb3c449))

- **ci**: Bump codecov/codecov-action in the github-actions group
  ([#307](https://github.com/sblibs/pySwitchbot/pull/307),
  [`e11bce8`](https://github.com/sblibs/pySwitchbot/commit/e11bce8b91c3566ea293037a1d4441e95bb3c449))

- **pre-commit.ci**: Pre-commit autoupdate ([#308](https://github.com/sblibs/pySwitchbot/pull/308),
  [`eb262e2`](https://github.com/sblibs/pySwitchbot/commit/eb262e2696d9c52c9e1c56ebe6dedaa030da68d8))


## v0.57.0 (2025-02-28)

### Chores

- Address some of the lint issues
  ([`98b42dc`](https://github.com/sblibs/pySwitchbot/commit/98b42dc4bfa1fd11fd4b3000ae6ecbc3b76c1003))

- **pre-commit.ci**: Auto fixes
  ([`98b42dc`](https://github.com/sblibs/pySwitchbot/commit/98b42dc4bfa1fd11fd4b3000ae6ecbc3b76c1003))


## v0.56.1 (2025-02-28)

### Bug Fixes

- Background tasks getting garbage collected before they finish
  ([#301](https://github.com/sblibs/pySwitchbot/pull/301),
  [`df11f76`](https://github.com/sblibs/pySwitchbot/commit/df11f7624ace66eb9cf70068541064a5fee37d19))

### Chores

- Add additional ruff config ([#302](https://github.com/sblibs/pySwitchbot/pull/302),
  [`d8bf41d`](https://github.com/sblibs/pySwitchbot/commit/d8bf41dd7b5508b55ca2f52c07dc436c0a1f13ad))

- **ci**: Bump the github-actions group with 2 updates
  ([#295](https://github.com/sblibs/pySwitchbot/pull/295),
  [`0311eba`](https://github.com/sblibs/pySwitchbot/commit/0311eba80ab5be255d9850d120b71827aeeab90c))

- **pre-commit.ci**: Pre-commit autoupdate ([#305](https://github.com/sblibs/pySwitchbot/pull/305),
  [`e91083e`](https://github.com/sblibs/pySwitchbot/commit/e91083eb486b4ccef2377d0faa3770f71da29fb3))

- **pre-commit.ci**: Pre-commit autoupdate ([#300](https://github.com/sblibs/pySwitchbot/pull/300),
  [`b3930db`](https://github.com/sblibs/pySwitchbot/commit/b3930dbcdfc3e03bfb33fe673776f0c6bfaed158))

- **pre-commit.ci**: Pre-commit autoupdate ([#298](https://github.com/sblibs/pySwitchbot/pull/298),
  [`e128512`](https://github.com/sblibs/pySwitchbot/commit/e1285127eef135147843d0e167c15ab7367cc92d))


## v0.56.0 (2025-01-30)

### Chores

- **pre-commit.ci**: Pre-commit autoupdate ([#291](https://github.com/sblibs/pySwitchbot/pull/291),
  [`c1b531d`](https://github.com/sblibs/pySwitchbot/commit/c1b531d54a913530fabecc0007a95a5e8d45e6de))

- **pre-commit.ci**: Pre-commit autoupdate ([#289](https://github.com/sblibs/pySwitchbot/pull/289),
  [`949f8b9`](https://github.com/sblibs/pySwitchbot/commit/949f8b9c0df88169bd8aa4614a6d58a3c90ad3a8))

- **pre-commit.ci**: Pre-commit autoupdate ([#288](https://github.com/sblibs/pySwitchbot/pull/288),
  [`bef9beb`](https://github.com/sblibs/pySwitchbot/commit/bef9bebac1a17e8c989d343d40dca786535d149e))

- **pre-commit.ci**: Pre-commit autoupdate ([#286](https://github.com/sblibs/pySwitchbot/pull/286),
  [`6edd68c`](https://github.com/sblibs/pySwitchbot/commit/6edd68ca5e2405bde2f661bbcf1ffbeeb05a33c8))


## v0.55.4 (2024-12-22)


## v0.55.3 (2024-12-22)


## v0.55.2 (2024-12-20)


## v0.55.1 (2024-12-20)


## v0.55.0 (2024-12-20)

### Chores

- Switch to ruff, set minimum python version
  ([#278](https://github.com/sblibs/pySwitchbot/pull/278),
  [`8f3172a`](https://github.com/sblibs/pySwitchbot/commit/8f3172a216090c0b03945d5a7d2aa883f68a9149))

- **pre-commit.ci**: Pre-commit autoupdate ([#276](https://github.com/sblibs/pySwitchbot/pull/276),
  [`1ebac33`](https://github.com/sblibs/pySwitchbot/commit/1ebac332250a43e5d41f2b261d42cbfe08fb4da2))

- **pre-commit.ci**: Pre-commit autoupdate ([#275](https://github.com/sblibs/pySwitchbot/pull/275),
  [`2b2707d`](https://github.com/sblibs/pySwitchbot/commit/2b2707d2ed191240c96bf8aa1977db0a115cd4ae))


## v0.54.0 (2024-11-26)

### Chores

- **pre-commit.ci**: Pre-commit autoupdate ([#273](https://github.com/sblibs/pySwitchbot/pull/273),
  [`6f297c9`](https://github.com/sblibs/pySwitchbot/commit/6f297c940a44c1cbd6cefca667f7f9113a8fa7d6))


## v0.53.2 (2024-11-18)


## v0.53.1 (2024-11-18)


## v0.53.0 (2024-11-17)


## v0.52.0 (2024-11-17)


## v0.51.0 (2024-10-22)


## v0.50.1 (2024-10-21)


## v0.50.0 (2024-10-21)


## v0.49.0 (2024-10-21)


## v0.48.2 (2024-08-22)


## v0.48.0 (2024-06-18)

### Bug Fixes

- Drop python 3.10 support since it does not have StrEnum
  ([#242](https://github.com/sblibs/pySwitchbot/pull/242),
  [`93ecb3a`](https://github.com/sblibs/pySwitchbot/commit/93ecb3aabd00285b396899f1a3e065e0cd7186ba))


## v0.47.2 (2024-05-31)


## v0.47.1 (2024-05-31)


## v0.47.0 (2024-05-31)


## v0.46.1 (2024-05-23)


## v0.46.0 (2024-05-23)


## v0.44.1 (2024-01-24)


## v0.44.0 (2024-01-11)

### Bug Fixes

- Missing coverage report ([#227](https://github.com/sblibs/pySwitchbot/pull/227),
  [`a197e13`](https://github.com/sblibs/pySwitchbot/commit/a197e13b30889ac3b58172212dfc8f1e57cd463b))


## v0.43.0 (2024-01-01)


## v0.42.0 (2023-12-20)


## v0.41.0 (2023-11-11)


## v0.40.1 (2023-09-30)


## v0.40.0 (2023-09-16)


## v0.39.1 (2023-08-29)


## v0.39.0 (2023-08-17)


## v0.38.0 (2023-06-19)

### Features

- Wolock example ([#211](https://github.com/sblibs/pySwitchbot/pull/211),
  [`d60b281`](https://github.com/sblibs/pySwitchbot/commit/d60b28114971b4ceb7faf9e7c51af31536b7cfaf))


## v0.37.6 (2023-04-06)


## v0.37.5 (2023-03-26)


## v0.37.4 (2023-03-22)


## v0.37.3 (2023-02-20)


## v0.37.2 (2023-02-20)


## v0.37.1 (2023-01-29)


## v0.37.0 (2023-01-25)


## v0.36.4 (2023-01-12)


## v0.36.3 (2023-01-06)


## v0.36.2 (2023-01-05)


## v0.36.1 (2022-12-31)


## v0.36.0 (2022-12-30)

### Features

- Wrap requests exceptions in SwitchbotAccountConnectionError
  ([#175](https://github.com/sblibs/pySwitchbot/pull/175),
  [`aa4b033`](https://github.com/sblibs/pySwitchbot/commit/aa4b0332a75a59131a96e0c1933d02b85896ba00))


## v0.35.0 (2022-12-30)

### Bug Fixes

- Ensure lock state is reflected when operated manually while connected
  ([#173](https://github.com/sblibs/pySwitchbot/pull/173),
  [`a34072f`](https://github.com/sblibs/pySwitchbot/commit/a34072f38844cf6383baa37283c3949bd3c05a56))

### Features

- Add SwitchbotAuthenticationError exception
  ([#174](https://github.com/sblibs/pySwitchbot/pull/174),
  [`93ac70e`](https://github.com/sblibs/pySwitchbot/commit/93ac70e5267b030d8ecb5c4e398f5094cc935e3e))


## v0.34.1 (2022-12-29)


## v0.34.0 (2022-12-29)


## v0.33.0 (2022-12-27)


## v0.32.1 (2022-12-27)


## v0.32.0 (2022-12-26)


## v0.31.0 (2022-12-26)


## v0.30.1 (2022-12-23)


## v0.30.0 (2022-12-20)


## v0.29.1 (2022-12-18)


## v0.29.0 (2022-12-18)


## v0.28.0 (2022-12-17)


## v0.27.1 (2022-12-16)


## v0.27.0 (2022-12-16)


## v0.26.3 (2022-12-16)


## v0.26.2 (2022-12-16)


## v0.26.1 (2022-12-16)


## v0.26.0 (2022-12-16)


## v0.25.0 (2022-12-16)


## v0.24.0 (2022-12-16)


## v0.23.2 (2022-12-14)


## v0.23.1 (2022-12-09)


## v0.23.0 (2022-12-09)


## v0.22.0 (2022-12-04)


## v0.21.0 (2022-12-04)


## v0.20.8 (2022-12-03)


## v0.20.7 (2022-12-02)


## v0.20.6 (2022-12-02)


## v0.20.5 (2022-11-14)


## v0.20.4 (2022-11-13)


## v0.20.3 (2022-11-10)

### Bug Fixes

- Lower disconnect delay to 8.5 seconds ([#135](https://github.com/sblibs/pySwitchbot/pull/135),
  [`5aad199`](https://github.com/sblibs/pySwitchbot/commit/5aad199af8100bbabd41f1d6e38ce872a5b2df52))


## v0.20.2 (2022-10-16)


## v0.20.1 (2022-10-16)


## v0.20.0 (2022-10-15)


## v0.19.15 (2022-10-09)


## v0.19.14 (2022-10-04)


## v0.19.13 (2022-09-27)

### Bug Fixes

- Crash on checking humidifier adv ([#125](https://github.com/sblibs/pySwitchbot/pull/125),
  [`1413c1f`](https://github.com/sblibs/pySwitchbot/commit/1413c1f8c28435620c2a202c91a6c4a1e35a6fc1))


## v0.19.12 (2022-09-27)

### Bug Fixes

- Handle new switchbot firmwares ([#124](https://github.com/sblibs/pySwitchbot/pull/124),
  [`f1be36b`](https://github.com/sblibs/pySwitchbot/commit/f1be36bfb63ee7bbc617aff5a7ad9717737c88d2))


## v0.19.11 (2022-09-20)


## v0.19.10 (2022-09-18)


## v0.19.9 (2022-09-15)


## v0.19.8 (2022-09-13)


## v0.19.7 (2022-09-13)


## v0.19.6 (2022-09-12)


## v0.19.5 (2022-09-11)


## v0.19.4 (2022-09-11)


## v0.19.3 (2022-09-10)


## v0.19.2 (2022-09-10)

### Features

- Expose get_device api ([#106](https://github.com/sblibs/pySwitchbot/pull/106),
  [`6159f90`](https://github.com/sblibs/pySwitchbot/commit/6159f90e743c3c7f50beffb45b17eddd48d31b08))


## v0.19.1 (2022-09-09)


## v0.19.0 (2022-09-08)


## v0.18.27 (2022-09-07)


## v0.18.26 (2022-09-07)


## v0.18.25 (2022-09-06)


## v0.18.24 (2022-09-06)


## v0.18.23 (2022-09-06)


## v0.18.22 (2022-09-01)

### Bug Fixes

- Cleanup some debug log messages ([#94](https://github.com/sblibs/pySwitchbot/pull/94),
  [`dc97b48`](https://github.com/sblibs/pySwitchbot/commit/dc97b48bd7fa99f241b6e85ed40b0b3191ff1df8))


## v0.18.21 (2022-08-28)

### Bug Fixes

- Reject advertisement updates that are missing data if we already have it
  ([#93](https://github.com/sblibs/pySwitchbot/pull/93),
  [`1ebcc8c`](https://github.com/sblibs/pySwitchbot/commit/1ebcc8cabebf03f1fc742680b36870a124158c76))


## v0.18.20 (2022-08-28)

### Bug Fixes

- Logging for sequence devices ([#91](https://github.com/sblibs/pySwitchbot/pull/91),
  [`031e9af`](https://github.com/sblibs/pySwitchbot/commit/031e9afd3b5a24399cb850ae28255e24c34425a6))

- Override the stale adv when making a change ([#92](https://github.com/sblibs/pySwitchbot/pull/92),
  [`700be22`](https://github.com/sblibs/pySwitchbot/commit/700be22493c1fed64c81de706b667c63b9ad1bc6))


## v0.18.19 (2022-08-28)

### Bug Fixes

- Return None when there is no response instead of an empty byte so we can give a better error
  ([#90](https://github.com/sblibs/pySwitchbot/pull/90),
  [`5f25d59`](https://github.com/sblibs/pySwitchbot/commit/5f25d59572b7866828dceba28ef5b93b6c3b2ace))


## v0.18.18 (2022-08-28)

### Bug Fixes

- Small fixes for light strips ([#89](https://github.com/sblibs/pySwitchbot/pull/89),
  [`8e88df6`](https://github.com/sblibs/pySwitchbot/commit/8e88df6b7fddc658eee226b93f043eb3522c90be))

### Features

- Add support for light strips ([#88](https://github.com/sblibs/pySwitchbot/pull/88),
  [`bcb954a`](https://github.com/sblibs/pySwitchbot/commit/bcb954af4a5bc2fd16598346aeb2980a1d8784f2))


## v0.18.17 (2022-08-28)

### Bug Fixes

- Report rssi when device is on the edge of range
  ([#87](https://github.com/sblibs/pySwitchbot/pull/87),
  [`2c98806`](https://github.com/sblibs/pySwitchbot/commit/2c98806e98a303daa6e6c4ded18c0a3cc645be9f))


## v0.18.16 (2022-08-28)

### Bug Fixes

- Add a guard to the bulb to reject invalid state updates
  ([#86](https://github.com/sblibs/pySwitchbot/pull/86),
  [`f19fd1c`](https://github.com/sblibs/pySwitchbot/commit/f19fd1cad274c0b04d9aaa87f67cc294cfcaebe6))


## v0.18.15 (2022-08-27)


## v0.18.14 (2022-08-20)


## v0.18.13 (2022-08-20)


## v0.18.11 (2022-08-19)


## v0.8.11 (2022-08-19)


## v0.18.10 (2022-08-14)


## v0.18.9 (2022-08-14)


## v0.18.8 (2022-08-14)


## v0.18.7 (2022-08-12)

### Bug Fixes

- Add guard to parse_advertisement_data for empty data
  ([#73](https://github.com/sblibs/pySwitchbot/pull/73),
  [`da189e6`](https://github.com/sblibs/pySwitchbot/commit/da189e6651f3e03107433128873b6fe17f017f1f))


## v0.18.6 (2022-08-11)


## v0.18.5 (2022-08-11)


## v0.18.4 (2022-08-05)


## v0.18.3 (2022-08-05)


## v0.18.2 (2022-08-05)


## v0.18.1 (2022-08-04)


## v0.18.0 (2022-08-04)


## v0.17.3 (2022-08-02)


## v0.17.2 (2022-08-02)

### Features

- Add basic support for the color bulbs ([#57](https://github.com/sblibs/pySwitchbot/pull/57),
  [`87752a9`](https://github.com/sblibs/pySwitchbot/commit/87752a94fadf9f2fd132437bfdd6a840a51160ee))


## v0.17.1 (2022-08-01)


## v0.17.0 (2022-08-01)

### Bug Fixes

- Wifi rssi incorrect on plugs (should be negative)
  ([#56](https://github.com/sblibs/pySwitchbot/pull/56),
  [`9f921db`](https://github.com/sblibs/pySwitchbot/commit/9f921dbe3c3ab2f9efe381cc1bfe09d7b1adfae7))


## v0.16.0 (2022-07-31)


## v0.15.2 (2022-07-26)


## v0.15.1 (2022-07-24)


## v0.15.0 (2022-07-23)


## v0.14.1 (2022-07-20)


## v0.14.0 (2022-06-21)


## v0.13.3 (2022-02-21)


## v0.13.2 (2022-01-09)


## v0.13.1 (2022-01-08)


## v0.13.0 (2021-11-08)


## v0.12.0 (2021-10-09)


## v0.11.0 (2021-06-19)


## v0.10.1 (2021-06-06)


## v0.10.0 (2021-05-12)

### Bug Fixes

- Read wrong position state
  ([`8965ddb`](https://github.com/sblibs/pySwitchbot/commit/8965ddb946dc06a6f382c2abccd4517bf7566605))

- Read wrong position state, now minimum time between update and last command
  ([`8965ddb`](https://github.com/sblibs/pySwitchbot/commit/8965ddb946dc06a6f382c2abccd4517bf7566605))

- Resolve conversation on Line 150 - 153 in #21
  ([`8965ddb`](https://github.com/sblibs/pySwitchbot/commit/8965ddb946dc06a6f382c2abccd4517bf7566605))

- Reverse reading position
  ([`8965ddb`](https://github.com/sblibs/pySwitchbot/commit/8965ddb946dc06a6f382c2abccd4517bf7566605))


## v0.9.1 (2020-12-20)


## v0.9.0 (2020-12-18)

### Bug Fixes

- Pylint and docsstrings
  ([`56308c2`](https://github.com/sblibs/pySwitchbot/commit/56308c2145b8d4f38c1bc5a0dceccdabc562fb7e))

- Stop key adjusted after local testing ([#14](https://github.com/sblibs/pySwitchbot/pull/14),
  [`1b28660`](https://github.com/sblibs/pySwitchbot/commit/1b28660bc28cae6b0b2928f7986030b321edc0fc))


## v0.8.0 (2019-12-29)


## v0.7.0 (2019-11-22)


## v0.6.2 (2019-05-06)


## v0.6.1 (2019-05-02)

- Initial Release
