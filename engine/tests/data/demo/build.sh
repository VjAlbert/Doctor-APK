#!/bin/sh
# Rebuilds classes.dex from the Java sources. Needs a JDK and the `dx` tool from Maven Central:
#   com.jakewharton.android.repackaged:dalvik-dx:9.0.0_r3  (pass its jar as $1)
set -e
DX="${1:?usage: build.sh path/to/dalvik-dx.jar}"
cd "$(dirname "$0")"
rm -rf out && mkdir -p out/stubs out/classes
javac --release 8 -d out/stubs $(find stubs -name '*.java')
javac --release 8 -cp out/stubs -d out/classes $(find app -name '*.java')
java -cp "$DX" com.android.dx.command.Main --dex --output=classes.dex out/classes
rm -rf out
