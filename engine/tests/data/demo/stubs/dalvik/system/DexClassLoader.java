package dalvik.system;

public class DexClassLoader extends ClassLoader {
    public DexClassLoader(String dexPath, String optDir, String libPath, ClassLoader parent) { super(parent); }
}
