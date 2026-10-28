package com.example.demo;

import dalvik.system.DexClassLoader;

/** Loads extra code from a file at runtime. */
public class Updater {
    public static ClassLoader loadPlugin(String path) {
        return new DexClassLoader(path, "/data/local/tmp", null, Updater.class.getClassLoader());
    }
}
