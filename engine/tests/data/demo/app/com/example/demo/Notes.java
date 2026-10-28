package com.example.demo;

/** Harmless note helpers, unrelated to the sensitive features. */
public class Notes {
    public static String title(String text) {
        String first = text.trim().split("\n")[0];
        return first.length() > 20 ? first.substring(0, 20) + "..." : first;
    }

    public static int wordCount(String text) {
        return text.trim().isEmpty() ? 0 : text.trim().split("\\s+").length;
    }
}
