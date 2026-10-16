package com.godot.game.steam.cloud;

import android.content.Context;

import com.godot.game.steam.core.SteamSettings;

import java.io.File;
import java.util.Locale;

public final class Sts2SteamCloudPathMapper {
	private static final String AUTO_CLOUD_PREFIX = "%GameInstall%/";
	private static final String MODDED_PREFIX = "modded/";
	private final boolean includeSettingsSave;
	private final boolean moddedAsMain;

	public Sts2SteamCloudPathMapper(Context context) {
		this(SteamSettings.shouldSyncSettingsSave(context), SteamSettings.shouldSyncModdedAsMain(context));
	}

	Sts2SteamCloudPathMapper(boolean includeSettingsSave, boolean moddedAsMain) {
		this.includeSettingsSave = includeSettingsSave;
		this.moddedAsMain = moddedAsMain;
	}

	public String toLocalRelativePath(String remotePath) {
		String normalized = normalize(remotePath);
		if (normalized.regionMatches(true, 0, AUTO_CLOUD_PREFIX, 0, AUTO_CLOUD_PREFIX.length())) {
			normalized = normalized.substring(AUTO_CLOUD_PREFIX.length());
		}
		if (!isSupportedPath(normalized)) {
			return "";
		}
		if (!moddedAsMain) {
			return normalized;
		}
		// Local fork patch (PATCHES.md): the cloud's regular saves live in the local modded set.
		// Cloud modded/ files are ignored so they cannot collide with that mapping.
		String lower = normalized.toLowerCase(Locale.ROOT);
		if (lower.startsWith(MODDED_PREFIX)) {
			return "";
		}
		return "settings.save".equals(lower) ? normalized : MODDED_PREFIX + normalized;
	}

	public String toRemotePath(String localRelativePath) {
		String normalized = normalize(localRelativePath);
		if (!isSupportedPath(normalized)) {
			return "";
		}
		if (!moddedAsMain) {
			return normalized;
		}
		String lower = normalized.toLowerCase(Locale.ROOT);
		if ("settings.save".equals(lower)) {
			return normalized;
		}
		// The local regular save set is not synced in this mode; it would overwrite the same cloud paths.
		return lower.startsWith(MODDED_PREFIX) ? normalized.substring(MODDED_PREFIX.length()) : "";
	}

	public boolean isSupportedLocalPath(String localRelativePath) {
		return !toRemotePath(localRelativePath).isEmpty();
	}

	private boolean isSupportedPath(String relativePath) {
		String path = normalize(relativePath);
		if (path.isEmpty() || path.contains(":")) {
			return false;
		}
		String[] parts = path.split("/");
		for (String part : parts) {
			if (part.isEmpty() || ".".equals(part) || "..".equals(part)) {
				return false;
			}
		}
		String lower = path.toLowerCase(Locale.ROOT);
		if ("profile.save".equals(lower) || "modded/profile.save".equals(lower)) {
			return true;
		}
		if ("settings.save".equals(lower)) {
			return includeSettingsSave;
		}
		return isProfileSavePath(lower, "") || isProfileSavePath(lower, "modded/");
	}

	public File resolveLocalFile(File accountRoot, String localRelativePath) {
		String normalized = normalize(localRelativePath);
		File file = new File(accountRoot, normalized.replace('/', File.separatorChar));
		try {
			String rootPath = accountRoot.getCanonicalPath();
			String filePath = file.getCanonicalPath();
			if (!filePath.equals(rootPath) && !filePath.startsWith(rootPath + File.separator)) {
				throw new IllegalArgumentException("Cloud path escapes account root: " + localRelativePath);
			}
		} catch (Exception exception) {
			throw new IllegalArgumentException("Invalid cloud path: " + localRelativePath, exception);
		}
		return file;
	}

	private boolean isProfileSavePath(String lower, String prefix) {
		for (int slot = 1; slot <= 3; slot++) {
			String base = prefix + "profile" + slot + "/saves/";
			if ((base + "progress.save").equals(lower)
				|| (base + "prefs.save").equals(lower)
				|| (base + "current_run.save").equals(lower)
				|| (base + "current_run.save.backup").equals(lower)
				|| (base + "current_run_mp.save").equals(lower)
				|| (base + "current_run_mp.save.backup").equals(lower)) {
				return true;
			}
			String history = base + "history/";
			if (lower.startsWith(history) && lower.endsWith(".run") && lower.length() > history.length() + 4) {
				return true;
			}
		}
		return false;
	}

	private String normalize(String path) {
		String value = path == null ? "" : path.trim().replace('\\', '/');
		while (value.startsWith("/")) {
			value = value.substring(1);
		}
		while (value.contains("//")) {
			value = value.replace("//", "/");
		}
		return value;
	}
}
