# PATCHES.md

這份是 Jason 的 Sts2MobileLauncher fork（`jason5545/Sts2MobileLauncher`）相對 upstream（`ModinMobileSTS/Sts2MobileLauncher`）保留的本地 patch 清單，以及在這台 Mac 上 build 的方法。本機 clone 的 `origin` 是 fork，`upstream` 是原專案；直接在 `main` 上 commit。

- Upstream 基準：`main` 的 `879a8a8`（feat: add opt-in portrait display mode，2026-10-08），`port-mod` submodule 在 `a63909c`。
- 測試機：25102PCBEG（代號 myron）、Android 16、arm64。遊戲 v0.111.0，payload `sts2-v0.111.0-41cef1ea-0861bfa1df34`。
- 起因：[#99](https://github.com/ModinMobileSTS/Sts2MobileLauncher/issues/99) 的直向模式 10/8 合進 `main`，但最新發布版 v0.1.11 是 10/2 出的，沒有這個功能，repo 也沒有 CI 產物。

維護規則：

- 新增本地 patch：在「保留的本地改動」加一條（為什麼要改、相關檔案、怎麼驗證），在「合併衝突檢查」列出要守的檔案，並更新條數。
- upstream 修了同一件事：確認行為一致後整段換成 upstream 版，兩處一起拿掉。
- 建置方法有變（換基準 commit、換遊戲版本、換手機上的 APK 來源）就更新「建置與安裝」，連同日期。

## 建置與安裝

完整建置要的 Godot/Mono runtime、FMOD AAR 和每個遊戲版本的原版 DLL 都不在 repo 裡，也沒有公開來源。這裡的做法是：Java/Kotlin 和 compat 從原始碼編，原生二進位從手機上已裝的 v0.1.11 APK 抽出來補。v0.1.11 到 `879a8a8` 之間 `tools/android/fmod-shim`、`android/build.gradle`、`offline-bootstrap/` 都沒有改，所以可以這樣補。

手機上裝了關閉簽名驗證的模組。這裡用 `~/.android/debug.keystore` 簽，跟官方 APK 的簽名不同，靠那個模組才能 `adb install -r` 原地覆蓋。資料（payload、MOD、存檔、啟動設定檔、Steam 登入）都會保留。

1. 備份。app 是 debuggable，可以用 `run-as`：
   `adb exec-out run-as com.megacrit.sts2re tar -cf - files shared_prefs > .agent/device-backup/<日期>/sts2re-data.tar`
   2026-10-16 那份在 `.agent/device-backup/2026-10-16/`，2.6 GB、2938 個檔案。
2. 拉 APK 和參考 DLL：
   - `adb shell pm path com.megacrit.sts2re` 拿到 `base.apk` 路徑後 `adb pull`，解開，再用 `d2j-dex2jar` 轉成 `all.jar`。
   - 原版 DLL 從手機 payload 拉到 `.agent/refs/original-v0.111.0/`：`files/payloads/<payload>/game/data_sts2_windows_x86_64/` 底下的 `sts2.dll`、`GodotSharp.dll`、`0Harmony.dll`。`sts2.dll` 的 SHA-256 是 `0861bfa1…`，跟 `port-mod/targets/active/v0.111.0/target.json` 記的一致。
3. 組 `android/libs/release/`（整個目錄在 `.gitignore` 裡）：
   - `godot-lib.template_release.aar`：Maven Central 的 `org.godotengine:godot:4.5.1.stable`，只留 `jni/arm64-v8a`，把 `libgodot_android.so` 換成 APK 裡那顆（Mono 版，70256104 bytes）。APK 裡的 `org.godotengine` 類別跟官方 AAR 只差 D8 產生的 lambda，`R` 的 88 筆資源完全相同。換完跑 `tools/android/patch-godot-input-pool.py <aar> --javac <JDK21>/bin/javac --android-jar <sdk>/platforms/android-35/android.jar`，再用 `--check` 確認。
   - `arm64-v8a/`：APK `lib/arm64-v8a/` 的 `.so` 全部放進來，**除了** `libgodot_android.so`、`libc++_shared.so`（已在 AAR 裡）、`libworkshop_zstd.so`、`libmonomod_android_libc_shim.so`（這兩顆是專案自己用 CMake 編的，重複放會在 `mergeMonoReleaseNativeLibs` 失敗）。
   - `fmod-release.aar`：從 `all.jar` 取 `org/fmod/*` 和 `com/utopiarise/*`（去掉空的 `R.class`）包成 `classes.jar`，`R.txt` 留空。AAR 的 `AndroidManifest.xml` **一定要**帶 `<meta-data android:name="org.godotengine.plugin.v2.FmodPlugin" android:value="com.utopiarise.godot.fmod.android.plugin.FmodPlugin"/>`。這段原本是官方 FMOD AAR 的 manifest 帶進來的，專案的 manifest 沒有，只給 jar 的話 Godot 不會載入 FMOD 外掛。
   - `libSystem.Security.Cryptography.Native.Android.jar`：從 `all.jar` 取 `net/dot/*`。
   - `android/assets/dotnet_bcl/`：直接用 APK 的 `assets/dotnet_bcl/`（189 個檔）。裡面的 `MonoMod.Utils.dll` 已經是修過的版本（`0557…`），`libmonosgen-2.0.so` 是原版（`ccf7…`），都符合 `doc/build/building-and-packaging.md` §4.1、§4.2 的 SHA。
4. `.env` 只需要 `JAVA_HOME`（openjdk@21，Gradle 8.13 不能跑在 JDK 25/27 上）、`ANDROID_HOME`、`DOTNET_BIN`、`STS2_ORIGINAL_V1110_REFERENCE_DIR=.agent/refs/original-v0.111.0` 和 debug keystore 三項。SDK 要 `platforms;android-35` 和 `ndk;28.1.13356709`。
5. Compat 只編 v0.111.0：
   - `tools/android/build-port-mod.sh`（預設 flavor 就是 `original-v0.111.0`，輸出 `assets/dotnet_bcl/STS2Mobile.dll` 和 `assets/port_compat.pck`）。
   - `cd port-mod && DOTNET_BIN=/opt/homebrew/bin/dotnet ./tools/build-compat-matrix.sh --target v0.111.0`，把 `dist/compat-matrix/sts2-android-compat.zip` 複製到 `android/assets/compat_packs/`。這包只有 v0.111.0 一個 variant，換遊戲版本就要補對應的 `STS2_ORIGINAL_*` 參考 DLL 再編。
   - 離線啟動層沿用 APK 裡的 `assets/compat_packs/sts2-android-offline-bootstrap.zip`。在這台 Mac 跑 `offline-bootstrap/tools/build-offline-pack.sh` 會失敗：契約測試要在 arm64 的 .NET 裡載入 x86_64 的 `sts2.dll`，而且工具要 .NET 9 runtime（`DOTNET_ROLL_FORWARD=Major` 可以跑在 10 上，但架構問題還在）。
   - launcher 比對 compat zip 的 SHA，不同就重裝，所以新包會蓋掉手機上的舊包。
6. 不要跑 `tools/package/build_importer_apk.sh`，它第一步的 `sync-runtime-from-references.sh` 需要參考 runtime 目錄。直接跑 Gradle：
   `tools/android/gradle-with-s2-env.sh assembleMonoRelease -Prelease_keystore_file=$HOME/.android/debug.keystore -Prelease_keystore_password=android -Prelease_keystore_alias=androiddebugkey`
   產物在 `android/build/outputs/apk/mono/release/sts2-re.apk`，另存一份到 `dist/`。`main` 還沒升版號，裝好後仍顯示 v0.1.11（versionCode 113）。
7. 安裝前比對新舊 APK：`lib/` 和 `assets/`（BCL 除外）應該只有 compat zip、`port_compat.pck` 和 CMake 編的 shim 不同，`dotnet_bcl` 只有 `STS2Mobile.dll` 不同；`aapt2 dump xmltree` 要看得到 `FmodPlugin` 的 meta-data。然後 `adb shell am force-stop com.megacrit.sts2re && adb install -r <apk>`，確認 `dumpsys package` 的 `firstInstallTime` 沒變。

## 保留的本地改動

目前三條：

- **臺灣正體中文介面**：upstream 只有 `values-zh`（簡體）和 `values-zh-rTW/HK/MO/SG` 裡各一條簡體 app 名稱。Android 不會拿只標 `zh` 的資源去配 zh-Hant 的系統語言，所以繁中手機上除了 app 名稱，其他全部退回英文。
  - 檔案：`android/res/values-zh-rTW/` 底下 `strings_crash.xml`、`strings_game_settings.xml`、`strings_log_analysis.xml`、`strings_log_detail.xml`（新增，約 1,570 條），`godot_project_name_string.xml` 改成「殺戮尖塔2」。
  - 產生方式：`python3 tools/zh-tw/s2tw.py`。先跑 OpenCC `s2twp`，再套腳本裡有順序的臺灣用語表（直向／橫向、帳號、連線、自訂、啟動設定檔、存取、權杖、行動驗證器、本機、目前、透過、區域網路、「」引號等），最後比對資源名稱、格式符號和跳脫字元要跟 `values-zh` 完全相同。譯文不要手改，改用語表再重跑，不然下次重產會被蓋掉。
  - 用詞底線：cloud 一律「雲端」（「雲存檔」→「雲端存檔」）；rotation 的 portrait 譯「直向」，landscape 譯「橫向」；launch profile 譯「啟動設定檔」，避免跟「設定」頁撞名；MOD 方案仍是「方案」；「遊戲本體」「日誌」「預設」照留。
  - 驗證（2026-10-16，測試機）：設定頁、底部分頁、旋轉模式下拉都顯示正體中文，旋轉模式出現「直向（需搭配直向 MOD）」。`python3 tools/zh-tw/s2tw.py --check` 回 `would update: nothing`。
  - 只有 `values-zh-rTW`；HK/MO 仍是 upstream 原樣。

- **直向模式啟動不先轉橫向**：upstream 的直向模式在 `GodotApp.onCreate` 裡才 `setRequestedOrientation(PORTRAIT)`，但 manifest 寫死 `sensorLandscape`。系統啟動 activity 時（`onCreate` 之前）就照 manifest 套用固定旋轉，要等 app 畫出第一個畫面才重新評估；Godot 載入完才畫第一格，所以整段載入（實測約 20 秒）都是橫向。2026-10-16 的 logcat：`START GodotApp` 20:21:54.632 → `applyFixedRotationTransform ... rotation=1` 54.646 → app 請求直向 54.690。
  - 做法：新增 `GodotPortraitApp`（`GodotApp` 的空子類別），manifest 宣告 `screenOrientation="portrait"`、`exported="false"`，其他屬性照抄 `GodotApp`。`GodotApp.launchActivityClass()` 在旋轉模式是直向時回傳它；遊戲已經在跑時沿用正在跑的那個 class，避免同一個 process 起第二個 Godot 引擎（換模式時由原本的 runtime `setRequestedOrientation` 處理）。`restartGameAndExitProcess` 照目前設定選 class，因為 process 隨即結束。
  - 檔案：`android/src/com/godot/game/GodotPortraitApp.java`（新增）、`GodotApp.java`（`readConfiguredScreenRotationMode`、`activityClassForConfiguredRotation`、`launchActivityClass`、`setRequestedOrientation` 覆寫，`createLaunchIntent` 和重啟改用它們）、`DebugAutomationReceiver.java`、`AndroidManifest.xml`。
  - 第二層：只換 activity 還不夠。Godot 的 `Main::setup2` 在 renderer 起來後，照遊戲專案設定 `display/window/handheld/orientation`（橫向）呼叫 `GodotIO.setScreenOrientation`，它直接 `godot.getActivity().setRequestedOrientation(...)`。2026-10-16 第一版實測：啟動瞬間是直向，Vulkan 初始化（`Vulkan 1.4.295 - Forward Mobile`）後 0.1 秒內被設成 `requestedOrientation=0`，約 17 秒後 compat 的 `applySelectedScreenOrientationFromGame` 才改回來。所以 `GodotApp` 覆寫 `setRequestedOrientation`：`applyConfiguredScreenOrientation` 先把模式存進 `configuredRotationMode`，模式是直向時，非直向的請求一律換成 `SCREEN_ORIENTATION_PORTRAIT`。執行中切換模式時，`applyConfiguredScreenOrientation` 會先更新欄位，所以不會擋到使用者自己的切換。
  - 沒處理：桌面長按捷徑（`res/xml/game_shortcuts.xml`、`settings_shortcuts.xml`）仍指向 `GodotApp`，從捷徑直接進遊戲時，啟動瞬間還是橫向（之後的 Godot 請求會被擋下）。
  - 驗證：見下方「未驗證」。

- **MOD 存檔按普通存檔同步（Steam Cloud）**：原版遊戲只要載入任何 MOD 就改用 `modded/profileN` 存檔（sts2.dll 的 `CheckShowModdedSaveFilePopup`、`Copying all unmodded saves to the modded save location`）。手機只裝純 UI 的直向 MOD（STS2Portrait＋RitsuLib）、PC 不裝 MOD 時，兩邊進度會分岔：PC 寫雲端的 `profile1/…`，手機讀寫本機 `modded/profile1/…`。upstream 的設計是兩套各自同步，加一個手動的「MOD 存檔轉移」。
  - 做法：Steam 雲端設定加開關「MOD 存檔按普通存檔同步」（`SteamSettings.KEY_SYNC_MODDED_AS_MAIN`，預設關）。開啟後 `Sts2SteamCloudPathMapper` 把雲端 `profileN/saves/*`、`profile.save` 對應到本機 `modded/` 底下；本機普通存檔不參與同步（會撞同一個雲端路徑）；雲端的 `modded/*` 忽略；`settings.save` 維持在根目錄、仍受原本的開關控制。同步狀態（baseline、衝突判斷）都以本機路徑為 key，切換後第一次同步因為沒有 baseline，內容不同的檔案會跳衝突讓使用者選，不會默默覆蓋。
  - 只改 Steam Cloud；WebDAV 的 `WebDavSavePathMapper` 沒動。
  - 檔案：`steam/core/SteamSettings.java`、`steam/cloud/Sts2SteamCloudPathMapper.java`、`SteamAccountActivity.java`（開關和說明）、三種語言的 `strings_game_settings.xml`（`steam_cloud_sync_modded_as_main`、`_hint`；正體由 `s2tw.py` 產生）、`test/.../SteamCloudPathMapperTest.java`（新增兩個測試）。
  - 測試：`tools/android/gradle-with-s2-env.sh testMonoReleaseUnitTest --tests 'com.godot.game.steam.cloud.*' --tests com.godot.game.CloudSyncSafetyTest --tests com.godot.game.ScreenRotationSettingsTest`，2026-10-16 共 19 個全過。
  - 測試機設定（2026-10-16）：雲端模式「啟動前拉取 + 乾淨退出後上傳」（`full_auto`），開啟這個開關，關掉「同時同步 settings.save」。
  - 為什麼要關 settings.save：原版 `SaveManager.SyncCloudToLocal`（ILSpy 反編譯 v0.111.0 `sts2.dll`）每次啟動先跑 `DeleteSettingsFromCloud`，雲端有 `settings.save` 就刪掉；`EnumerateCloudSyncTasks` 只拉 `profile.save`、`progress.save`、`current_run(_mp).save`、`prefs.save` 和戰績。設定本來就不走雲端，開著只會讓手機每次上傳、PC 每次刪。2026-10-16 20:52 曾誤傳一次（5580 bytes），PC 下次啟動會自己刪掉，不會套用到 PC。
  - 第一次切換後的實際同步（2026-10-16 20:52）：跳出 3 個衝突（`progress.save`、`prefs.save`、`current_run.save`；雲端是 10/4、10/8 的版本），選「保留本機」，上傳到雲端的 `profile1/saves/…`，批次 `result=OK`。之後 `baseline.json` 75 筆全部 local／remote SHA1 一致，`modded/profile1/…` 對應 `profile1/…`。
  - 同一天也手動把本機普通存檔 `profile1/` 複製到 `modded/profile1/`（41 個檔 SHA1 一致），舊的 MOD 存檔改名成 `modded/profile1.empty-20261016`，Mac 上的備份在 `.agent/device-backup/2026-10-16/modded-before-copy-2026-10-16.tar`。

## 合併衝突檢查

合併 upstream 後碰到下列檔案時逐項確認：

- `android/res/values-zh/*.xml`（upstream 改了簡中字串）：跑 `python3 tools/zh-tw/s2tw.py`，再跑 `--check`；OpenCC 新轉出的中國用語補進腳本的用語表。腳本提示 `values-zh` 有新的 `strings_*.xml` 時，加進 `FILES`。
- `android/res/values-zh-rTW/godot_project_name_string.xml`：upstream 追蹤的檔案。兩邊都改到時取這裡的版本（`git checkout --ours`），或直接重跑腳本。
- upstream 自己加了 `values-zh-rTW` 的完整翻譯：比對兩邊的用詞，決定保留哪份；保留 upstream 版就拿掉這條和 `tools/zh-tw/`。
- `android/AndroidManifest.xml` 的 `.GodotApp` 區塊：upstream 改了它的屬性（theme、configChanges、launchMode、meta-data 以外的子元素）時，同步到 `.GodotPortraitApp`，只保留 `screenOrientation="portrait"` 和 `exported="false"` 不同。
- `GodotApp.java` 的 `createLaunchIntent`、`restartGameAndExitProcess`、`applyConfiguredScreenOrientation`：upstream 新增其他啟動 GodotApp 的地方時，改用 `launchActivityClass()`；`grep -rn 'GodotApp.class' android/src` 應該只剩 `GodotApp.java` 裡的 `activityClassForConfiguredRotation`。
- `steam/cloud/Sts2SteamCloudPathMapper.java`：upstream 改了支援的存檔路徑（`isSupportedPath`）時，確認新模式的對應仍成立，跑 `SteamCloudPathMapperTest`。
- `SteamAccountActivity.java` 的雲端狀態卡片（`settingsSaveSwitch` 附近）和 `SteamSettings.java`。
- `tools/zh-tw/s2tw.py`、`GodotPortraitApp.java`、`PATCHES.md`：本地加的，upstream 沒有。

## 未驗證

- 2026-10-16 已在測試機實際遊玩（v0.111.0 compat、STS2Portrait＋RitsuLib、接續 17:06 的進行中對局）。FMOD 音效沒有特別確認。
- 直向啟動修正：2026-10-16 21:01 從 launcher 啟動實測，`GodotPortraitApp` 期間每 0.4 秒取樣 `dumpsys window displays` 共 85 次全是 `mRotation=0`；logcat 有 `Keeping portrait orientation; replaced requestedOrientation=0`（21:01:07.481）。只驗了 launcher 啟動，桌面捷徑和遊戲內重啟沒測。
- MOD 存檔按普通存檔同步：上傳已驗證（見上）；從雲端拉取到 `modded/`、PC 端接到手機進度，還沒驗證。
