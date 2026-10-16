package com.godot.game;

/**
 * Local fork patch (PATCHES.md): GodotApp declared with a fixed portrait orientation in the
 * manifest, so portrait launches start in portrait instead of rotating after Godot's first frame.
 * {@link GodotApp#launchActivityClass} picks it when the rotation mode is portrait.
 */
public class GodotPortraitApp extends GodotApp {
}
