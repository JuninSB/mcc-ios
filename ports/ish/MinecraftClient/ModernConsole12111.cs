using System;
using System.IO;
using System.Threading;
using MinecraftClient.Protocol.Handlers;
using MinecraftClient.Protocol.Session;

namespace MinecraftClient
{
    internal static class ModernConsole12111
    {
        public static int Run(SessionToken account)
        {
            int closing = 0;
            Thread prompt = null;
            ConsoleIO.WriteLine(Translations.ish_console_scope);
            try
            {
                using (var tcp = Proxy.ProxyHandler.newTcpClient(Settings.ServerIP, Settings.ServerPort, false))
                using (var session = new ModernSession12111(tcp))
                {
                    tcp.ReceiveTimeout = 60000;
                    Guid uuid;
                    if (!Guid.TryParse(account.PlayerID, out uuid) || uuid == Guid.Empty) uuid = Guid.NewGuid();
                    session.Login(Settings.ServerIP, (ushort)Settings.ServerPort, account.PlayerName, uuid, account.ID);
                    var play = new Play12111(session.Send);
                    try
                    {
                        while (Thread.VolatileRead(ref closing) == 0)
                        {
                            int id;
                            byte[] packet = session.Read(out id);
                            lock (play) play.Handle(id, packet);
                            if (play.DisconnectReason != null)
                            {
                                ConsoleIO.WriteLine(string.Format(Translations.ish_console_message, play.DisconnectReason));
                                return 1;
                            }
                            if (id == 0x77 || id == 0x21)
                                ConsoleIO.WriteLineFormatted(string.Format(Translations.ish_console_message, play.LastSystemMessage));
                            if (id == 0x3F && !play.LastPlayerMessageFiltered)
                                ConsoleIO.WriteLineFormatted(string.Format(Translations.ish_console_player_unverified,
                                    play.LastPlayerSender, play.LastPlayerMessage));
                            if (play.Joined && prompt == null)
                            {
                                ConsoleIO.WriteLine(Translations.ish_console_joined);
                                prompt = new Thread(() =>
                                {
                                    try
                                    {
                                        while (Thread.VolatileRead(ref closing) == 0)
                                        {
                                            string line = ConsoleIO.ReadLine();
                                            if (line == null || line.Trim() == "/exit" || line.Trim() == "/quit")
                                            {
                                                Interlocked.Exchange(ref closing, 1);
                                                session.Dispose();
                                                return;
                                            }
                                            try { lock (play) play.SendUnsignedChat(line); }
                                            catch (ArgumentException e) { ConsoleIO.WriteLine(string.Format(Translations.ish_console_error, e.Message)); }
                                            catch (NotSupportedException e) { ConsoleIO.WriteLine(string.Format(Translations.ish_console_error, e.Message)); }
                                        }
                                    }
                                    catch (IOException) { Interlocked.Exchange(ref closing, 1); session.Dispose(); }
                                    catch (System.Net.Sockets.SocketException) { Interlocked.Exchange(ref closing, 1); session.Dispose(); }
                                    catch (ObjectDisposedException) { }
                                });
                                prompt.IsBackground = true;
                                prompt.Start();
                            }
                        }
                    }
                    catch (IOException) { if (Thread.VolatileRead(ref closing) == 0) throw; }
                    catch (System.Net.Sockets.SocketException) { if (Thread.VolatileRead(ref closing) == 0) throw; }
                    catch (ObjectDisposedException) { if (Thread.VolatileRead(ref closing) == 0) throw; }
                    return 0;
                }
            }
            catch (Exception e)
            {
                ConsoleIO.WriteLine(string.Format(Translations.ish_console_error, e.Message));
                return 1;
            }
            finally
            {
                Interlocked.Exchange(ref closing, 1);
                if (prompt != null && prompt.IsAlive) { prompt.Abort(); prompt.Join(1000); }
            }
        }
    }
}
