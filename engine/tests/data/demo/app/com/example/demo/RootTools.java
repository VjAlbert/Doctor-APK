package com.example.demo;

public class RootTools {
    public static boolean isRooted() {
        try {
            Process p = Runtime.getRuntime().exec(new String[] {"su", "-c", "id"});
            return p.waitFor() == 0;
        } catch (Exception e) {
            return false;
        }
    }
}
