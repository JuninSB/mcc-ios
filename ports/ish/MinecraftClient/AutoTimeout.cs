using System;
using System.Threading;

namespace MinecraftClient
{
    /// <summary>
    /// Allow easy timeout on pieces of code
    /// </summary>
    /// <remarks>
    /// By ORelio - (c) 2014 - CDDL 1.0
    /// </remarks>
    public class AutoTimeout
    {
        /// <summary>
        /// Perform the specified action with specified timeout
        /// </summary>
        /// <param name="action">Action to run</param>
        /// <param name="timeout">Maximum timeout in milliseconds</param>
        /// <returns>True if the action finished whithout timing out</returns>
        public static bool Perform(Action action, int timeout)
        {
            return Perform(action, TimeSpan.FromMilliseconds(timeout));
        }

        /// <summary>
        /// Perform the specified action with specified timeout
        /// </summary>
        /// <param name="action">Action to run</param>
        /// <param name="timeout">Maximum timeout</param>
        /// <returns>True if the action finished whithout timing out</returns>
        public static bool Perform(Action action, TimeSpan timeout)
        {
            Exception failure = null;
            Thread thread = new Thread(() =>
            {
                try { action(); }
                catch (ThreadAbortException) { throw; }
                catch (Exception e) { failure = e; }
            });
            thread.IsBackground = true;
            thread.Start();
            bool success = thread.Join(timeout);
            if (!success)
                thread.Abort();
            if (success && failure != null)
                throw failure;
            return success;
        }
    }
}
