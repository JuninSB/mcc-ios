using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace MinecraftClient.Protocol.Handlers
{
    /// <summary>
    /// Configuration control packets for protocol 774. IDs follow the modern MCC
    /// PacketPalette1219/1216 configuration tables, also used by 1.21.11.
    /// Registry/chat data and server policies remain the caller's responsibility.
    /// Not yet exposed as a supported connection version by the legacy runtime.
    /// </summary>
    public sealed class Configuration12111
    {
        private readonly DataTypes types = new DataTypes(774);
        public bool Finished { get; private set; }

        public bool TryReply(int packetId, byte[] payload, out int replyId, out byte[] reply)
        {
            ArgumentNullExceptionCheck(payload);
            replyId = -1;
            reply = null;
            if (Finished) throw new InvalidOperationException(Translations.ish_configuration_finished);
            switch (packetId)
            {
                case 0x03: // Finish configuration.
                    Require(payload.Length == 0);
                    replyId = 0x03;
                    reply = new byte[0];
                    Finished = true;
                    return true;
                case 0x04: // Keep alive: preserve all eight bytes, not a VarInt.
                    Require(payload.Length == 8);
                    replyId = 0x04;
                    reply = (byte[])payload.Clone();
                    return true;
                case 0x05: // Ping -> Pong, signed 32-bit opaque value.
                    Require(payload.Length == 4);
                    replyId = 0x05;
                    reply = (byte[])payload.Clone();
                    return true;
                case 0x00: // Cookie request. No cookie store is advertised yet.
                    var cookie = new Queue<byte>(payload);
                    string key = types.ReadNextString(cookie);
                    Require(cookie.Count == 0);
                    replyId = 0x01;
                    reply = types.GetString(key).Concat(new byte[] { 0 }).ToArray();
                    return true;
                case 0x0E: // Select known packs. Request full registry data from server.
                    var packs = new Queue<byte>(payload);
                    int count = types.ReadNextVarInt(packs);
                    Require(count >= 0 && count <= 1024);
                    for (int index = 0; index < count; index++)
                    {
                        types.ReadNextString(packs); // Namespace.
                        types.ReadNextString(packs); // ID.
                        types.ReadNextString(packs); // Version.
                    }
                    Require(packs.Count == 0);
                    replyId = 0x07;
                    reply = new byte[] { 0 };
                    return true;
                default:
                    // Do not auto-accept code of conduct/resource packs or suppress
                    // disconnects. The session must handle these explicitly.
                    return false;
            }
        }

        private static void ArgumentNullExceptionCheck(byte[] payload)
        {
            if (payload == null) throw new ArgumentNullException("payload");
        }

        private static void Require(bool condition)
        {
            if (!condition) throw new InvalidDataException(Translations.ish_packet_invalid);
        }
    }
}
