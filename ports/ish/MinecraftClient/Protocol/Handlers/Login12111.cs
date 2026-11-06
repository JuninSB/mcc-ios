using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace MinecraftClient.Protocol.Handlers
{
    /// <summary>Protocol-774 login payloads. Transport encryption/session checks stay in the session runtime.</summary>
    public sealed class Login12111
    {
        private readonly DataTypes types = new DataTypes(774);
        public bool Acknowledged { get; private set; }
        public Guid PlayerId { get; private set; }
        public string PlayerName { get; private set; }

        public byte[] CreateStart(string name, Guid playerId)
        {
            if (!ChatBot.IsValidName(name) || playerId == Guid.Empty) throw Invalid();
            return types.GetString(name).Concat(types.GetUUID(playerId)).ToArray();
        }

        // This parses a server response, not an authentication assertion. Microsoft
        // ownership and join-session checks are still required by online transport.
        public byte[] AcceptSuccess(Queue<byte> payload)
        {
            if (Acknowledged) throw Invalid();
            try
            {
                Guid id = types.ReadNextUUID(payload);
                string name = ReadString(payload);
                if (id == Guid.Empty || !ChatBot.IsValidName(name)) throw Invalid();
                int count = types.ReadNextVarInt(payload);
                if (count < 0 || count > 1024) throw Invalid();
                for (int index = 0; index < count; index++)
                {
                    ReadString(payload); // Property name.
                    ReadString(payload); // Property value.
                    byte signed = types.ReadNextByte(payload);
                    if (signed > 1) throw Invalid();
                    if (signed == 1) ReadString(payload); // Server-supplied property signature.
                }
                if (payload.Count != 0) throw Invalid();
                PlayerId = id;
                PlayerName = name;
                Acknowledged = true;
                return new byte[0]; // Login Acknowledged (serverbound ID 0x03).
            }
            catch (InvalidOperationException) { throw Invalid(); }
        }

        public byte[] DeclinePlugin(Queue<byte> payload)
        {
            try
            {
                int transaction = types.ReadNextVarInt(payload);
                ReadString(payload); // Channel. Remaining bytes are opaque plugin data.
                payload.Clear();
                return types.GetVarInt(transaction).Concat(new byte[] { 0 }).ToArray();
            }
            catch (InvalidOperationException) { throw Invalid(); }
        }

        private string ReadString(Queue<byte> payload)
        {
            int length = types.ReadNextVarInt(payload);
            if (length < 0 || length > 131068 || length > payload.Count) throw Invalid();
            return System.Text.Encoding.UTF8.GetString(types.ReadData(length, payload));
        }

        private static InvalidDataException Invalid()
        {
            return new InvalidDataException(Translations.ish_packet_invalid);
        }
    }
}
