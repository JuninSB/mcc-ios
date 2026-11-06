using System;
using System.IO;
using System.Linq;
using MinecraftClient.Crypto.Streams;

internal static class IshCrypto
{
    private static int Main(string[] args)
    {
        if (args.Length == 1 && args[0] == "--timeout-failure")
        {
            try
            {
                MinecraftClient.AutoTimeout.Perform(() => { throw new InvalidOperationException("MCC_TIMEOUT_SENTINEL"); }, 5000);
                return 51;
            }
            catch (InvalidOperationException failure)
            {
                return failure.Message == "MCC_TIMEOUT_SENTINEL" ? 0 : 52;
            }
        }
        if (args.Length == 1 && args[0] == "--configuration") return ConfigurationChecks();
        if (args.Length == 1 && args[0] == "--network-text") return NetworkTextChecks();
        if (args.Length == 1 && args[0] == "--modern-login") return ModernLoginChecks();
        if (args.Length == 3 && (args[0] == "--modern-session" || args[0] == "--modern-probe" || args[0] == "--modern-command-probe" || args[0] == "--modern-say-probe" || args[0] == "--modern-listen-probe"))
        {
            using (var tcp = new System.Net.Sockets.TcpClient(args[1], int.Parse(args[2])))
            using (var session = new MinecraftClient.Protocol.Handlers.ModernSession12111(tcp))
            {
                tcp.ReceiveTimeout = args[0] == "--modern-listen-probe" ? 65000 : 5000;
                session.Login(args[1], ushort.Parse(args[2]), "PortTest", new Guid("00112233-4455-6677-8899-aabbccddeeff"), null);
                if (!session.ConfigurationFinished) return 41;
                var controls = new MinecraftClient.Protocol.Handlers.Play12111(session.Send);
                bool commandSent = false;
                var listenDeadline = DateTime.UtcNow.AddSeconds(60);
                int id;
                while (true)
                {
                    byte[] play = session.Read(out id);
                    if (args[0] == "--modern-listen-probe")
                    {
                        controls.Handle(id, play);
                        if (controls.DisconnectReason != null) { Console.WriteLine(controls.DisconnectReason); return 44; }
                        if (controls.Joined && !commandSent) { Console.WriteLine("LISTENING_FOR_SERVER_SAY"); commandSent = true; }
                        if ((id == 0x77 || id == 0x21) && controls.LastSystemMessage != null)
                        {
                            Console.WriteLine(controls.LastSystemMessage);
                            if (controls.LastSystemMessage.Contains("MCC_ISH_SERVER_MESSAGE_TEST")) return 0;
                        }
                        if (DateTime.UtcNow >= listenDeadline) return 47;
                        continue;
                    }
                    if (args[0] == "--modern-command-probe" || args[0] == "--modern-say-probe")
                    {
                        controls.Handle(id, play);
                        if (controls.DisconnectReason != null) return 44;
                        if (controls.Joined && !commandSent)
                        {
                            controls.SendUnsignedChat(args[0] == "--modern-say-probe" ? "/say MCC_ISH_SERVER_MESSAGE_TEST" : "/version");
                            commandSent = true;
                        }
                        if (commandSent && controls.LastSystemMessage != null && id == 0x77)
                        {
                            Console.WriteLine(controls.LastSystemMessage);
                            if (args[0] == "--modern-say-probe")
                            {
                                if (controls.LastSystemMessage.Contains("command.unknown.command") ||
                                    controls.LastSystemMessage.Contains("command.context.here") ||
                                    controls.LastSystemMessage.Contains("Unknown or incomplete command") ||
                                    controls.LastSystemMessage.Contains("permission") || controls.LastSystemMessage.Contains("Unknown command")) return 46;
                                if (controls.LastSystemMessage.Contains("MCC_ISH_SERVER_MESSAGE_TEST") &&
                                    !controls.LastSystemMessage.Contains("<--[HERE]")) return 0;
                            }
                            if (controls.LastSystemMessage.Contains("Paper") && controls.LastSystemMessage.Contains("1.21.11")) return 0;
                        }
                        continue;
                    }
                    if (args[0] == "--modern-probe")
                    {
                        controls.Handle(id, play);
                        if (controls.DisconnectReason != null) return 44;
                        if (controls.Joined)
                        {
                            Console.WriteLine("PROTOCOL_774_JOIN_GAME entity={0} seaLevel={1} secureChat={2}", controls.EntityId, controls.SeaLevel, controls.EnforcesSecureChat);
                            return 0;
                        }
                        continue;
                    }
                    if (id == 0x7fff)
                    {
                        if (!play.SequenceEqual(new byte[] { 42 }) || controls.LastSystemMessage != "hi" || controls.DisconnectReason != "bye" ||
                            !controls.Joined || controls.EntityId != 42 || controls.SeaLevel != 63 || controls.EnforcesSecureChat ||
                            controls.DimensionName != "minecraft:overworld" || controls.LastServerSender != "Server" ||
                            controls.LastPlayerMessage != "player fixture" || controls.LastPlayerSender != "FixturePlayer" ||
                            !controls.LastPlayerSignaturePresent || controls.LastPlayerSignatureVerified) return 42;
                        break;
                    }
                    if (!controls.Handle(id, play)) return 43;
                    if (id == 0x30)
                    {
                        if (controls.EnforcesSecureChat)
                        {
                            try { controls.SendUnsignedChat("must-not-send"); return 45; }
                            catch (NotSupportedException) { }
                        }
                        else
                        {
                            controls.SendUnsignedChat("ISH_CHAT_OUTBOUND");
                            controls.SendUnsignedChat("/version");
                        }
                    }
                }
            }
            return 0;
        }
        // Fixture key/IV and expected ciphertext are produced independently by OpenSSL.
        byte[] key = File.ReadAllBytes(args[0]);
        byte[] plain = File.ReadAllBytes(args[1]);
        byte[] expected = File.ReadAllBytes(args[2]);
        var encrypted = new MemoryStream();
        var writer = new MonoAesStream(encrypted, key);
        int offset = 0;
        while (offset < plain.Length)
        {
            int count = Math.Min(offset % 17 + 1, plain.Length - offset);
            writer.Write(plain, offset, count);
            offset += count;
        }
        writer.Flush();
        if (!expected.SequenceEqual(encrypted.ToArray())) return 1;
        var reader = new MonoAesStream(new MemoryStream(expected), key);
        var decoded = new MemoryStream();
        byte[] buffer = new byte[23];
        int read;
        while ((read = reader.Read(buffer, 0, buffer.Length)) > 0) decoded.Write(buffer, 0, read);
        if (!plain.SequenceEqual(decoded.ToArray())) return 2;
        if (reader.ReadByte() != -1) return 3;
        return 0;
    }

    private static int ConfigurationChecks()
    {
        var control = new MinecraftClient.Protocol.Handlers.Configuration12111();
        int id;
        byte[] reply;
        byte[] alive = { 0xff, 0, 1, 2, 3, 4, 5, 6 };
        if (!control.TryReply(4, alive, out id, out reply) || id != 4 || !alive.SequenceEqual(reply)) return 11;
        byte[] ping = { 0xff, 0, 1, 2 };
        if (!control.TryReply(5, ping, out id, out reply) || id != 5 || !ping.SequenceEqual(reply)) return 12;
        byte[] cookie = { 3, 97, 98, 99 };
        if (!control.TryReply(0, cookie, out id, out reply) || id != 1 || !reply.SequenceEqual(new byte[] { 3, 97, 98, 99, 0 })) return 13;
        byte[] known = { 1, 1, 97, 1, 98, 1, 99 };
        if (!control.TryReply(14, known, out id, out reply) || id != 7 || !reply.SequenceEqual(new byte[] { 0 })) return 14;
        if (control.TryReply(0x13, new byte[0], out id, out reply)) return 15;
        try { control.TryReply(4, new byte[1], out id, out reply); return 16; }
        catch (InvalidDataException) { }
        if (!control.TryReply(3, new byte[0], out id, out reply) || id != 3 || !control.Finished || reply.Length != 0) return 17;
        try { control.TryReply(3, new byte[0], out id, out reply); return 18; }
        catch (InvalidOperationException) { }
        return 0;
    }

    private static int NetworkTextChecks()
    {
        var text = new System.Collections.Generic.Queue<byte>(new byte[] { 8, 0, 2, 104, 105, 99 });
        if (MinecraftClient.Protocol.Handlers.NetworkText12111.Read(text).StringValue != "hi" || text.Dequeue() != 99) return 21;
        var compound = new System.Collections.Generic.Queue<byte>(new byte[] { 10, 8, 0, 4, 116, 101, 120, 116, 0, 2, 104, 105, 0, 99 });
        var parsed = MinecraftClient.Protocol.Handlers.NetworkText12111.Read(compound);
        if (parsed.Properties["text"].StringValue != "hi" || compound.Dequeue() != 99) return 22;
        var parser = typeof(MinecraftClient.Protocol.Handlers.NetworkText12111).Assembly
            .GetType("MinecraftClient.Protocol.ChatParser").GetMethod("ParseNetworkText");
        var rendering = new System.Collections.Generic.Queue<byte>(new byte[] { 10, 8, 0, 4, 116, 101, 120, 116, 0, 2, 104, 105, 0 });
        if ((string)parser.Invoke(null, new object[] { rendering }) != "hi") return 25;
        var list = new System.Collections.Generic.Queue<byte>(new byte[] { 9, 8, 0, 0, 0, 2, 0, 1, 97, 0, 1, 98 });
        parsed = MinecraftClient.Protocol.Handlers.NetworkText12111.Read(list);
        if (parsed.DataArray.Count != 2 || parsed.DataArray[1].StringValue != "b") return 23;
        foreach (byte[] malformed in new[] { new byte[] { 8, 0, 10, 97 }, new byte[] { 9, 8, 127, 255, 255, 255 }, new byte[] { 13 } })
        {
            try { MinecraftClient.Protocol.Handlers.NetworkText12111.Read(new System.Collections.Generic.Queue<byte>(malformed)); return 24; }
            catch (InvalidDataException) { }
        }
        var nested = new System.Collections.Generic.List<byte>();
        for (int index = 0; index < 70; index++) nested.AddRange(new byte[] { 9, 9, 0, 0, 0, 1 });
        try { MinecraftClient.Protocol.Handlers.NetworkText12111.Read(new System.Collections.Generic.Queue<byte>(nested)); return 26; }
        catch (InvalidDataException) { }
        return 0;
    }

    private static int ModernLoginChecks()
    {
        var login = new MinecraftClient.Protocol.Handlers.Login12111();
        Guid uuid = new Guid("00112233-4455-6677-8899-aabbccddeeff");
        byte[] start = login.CreateStart("PortTest", uuid);
        byte[] wireUuid = { 0, 17, 34, 51, 68, 85, 102, 119, 136, 153, 170, 187, 204, 221, 238, 255 };
        if (!start.Take(9).SequenceEqual(new byte[] { 8, 80, 111, 114, 116, 84, 101, 115, 116 }) || !start.Skip(9).SequenceEqual(wireUuid)) return 31;
        var success = new System.Collections.Generic.List<byte>(wireUuid);
        success.AddRange(start.Take(9));
        success.AddRange(new byte[] { 1, 1, 97, 1, 98, 1, 1, 99 }); // One signed property.
        if (login.AcceptSuccess(new System.Collections.Generic.Queue<byte>(success)).Length != 0 || !login.Acknowledged || login.PlayerId != uuid || login.PlayerName != "PortTest") return 32;
        try { login.AcceptSuccess(new System.Collections.Generic.Queue<byte>(success)); return 33; }
        catch (InvalidDataException) { }
        var fresh = new MinecraftClient.Protocol.Handlers.Login12111();
        try { fresh.AcceptSuccess(new System.Collections.Generic.Queue<byte>(new byte[] { 0 })); return 34; }
        catch (InvalidDataException) { }
        byte[] declined = fresh.DeclinePlugin(new System.Collections.Generic.Queue<byte>(new byte[] { 7, 3, 97, 98, 99, 42 }));
        if (!declined.SequenceEqual(new byte[] { 7, 0 })) return 35;
        return 0;
    }
}
