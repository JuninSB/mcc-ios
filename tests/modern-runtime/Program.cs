using System;
using System.Runtime.CompilerServices;

// Bootstrap probe only, not an MCC implementation or a full runtime test.
// Exit 73 proves this exact managed entry point completed its checks.
internal static class Program
{
    private static int Main()
    {
        if (IntPtr.Size != 4 || !BitConverter.IsLittleEndian)
            return 10;
        if (typeof(object).Assembly.GetName().Version?.Major != 10)
            return 11;
        if (!RuntimeFeature.IsDynamicCodeSupported)
            return 12;
        object[] values = new object[256];
        for (int index = 0; index < values.Length; index++)
            values[index] = index;
        GC.Collect();
        for (int index = 0; index < values.Length; index++)
            if ((int)values[index] != index)
                return 13;
        return 73;
    }
}
