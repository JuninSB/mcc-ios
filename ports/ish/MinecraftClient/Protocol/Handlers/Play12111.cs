using System;
using System.Collections.Generic;
using System.IO;

namespace MinecraftClient.Protocol.Handlers
{
    /// <summary>Core play control for 1.21.11. Entity/world/inventory and signed player chat are not implemented here.</summary>
    public sealed class Play12111
    {
        private readonly Action<int, byte[]> send;
        private readonly DataTypes types = new DataTypes(774);
        private double x, y, z;
        private float yaw, pitch;
        private readonly Queue<string> acknowledgedSignatures = new Queue<string>();
        public string LastPlayerMessage { get; private set; }
        public string LastPlayerSender { get; private set; }
        public Guid LastPlayerId { get; private set; }
        public bool LastPlayerMessageFiltered { get; private set; }
        public bool LastPlayerSignaturePresent { get; private set; }
        public bool LastPlayerSignatureVerified { get { return false; } }
        public string LastSystemMessage { get; private set; }
        public string LastServerSender { get; private set; }
        public bool LastMessageIsOverlay { get; private set; }
        public string DisconnectReason { get; private set; }
        public bool Joined { get; private set; }
        public int EntityId { get; private set; }
        public int SeaLevel { get; private set; }
        public bool EnforcesSecureChat { get; private set; }
        public string DimensionName { get; private set; }

        public static byte[] ClientInformation()
        {
            var codec = new DataTypes(774);
            // Small view distance; normal chat, main hand right, minimal particles.
            return codec.ConcatBytes(codec.GetString("en_US"), new byte[] { 2, 0, 1, 0, 1, 0, 1, 2 });
        }

        public Play12111(Action<int, byte[]> sender)
        {
            if (sender == null) throw new ArgumentNullException("sender");
            send = sender;
        }

        public void SendUnsignedChat(string message)
        {
            if (!Joined) throw new InvalidOperationException(Translations.ish_chat_not_joined);
            if (EnforcesSecureChat) throw new NotSupportedException(Translations.ish_chat_secure_required);
            if (string.IsNullOrEmpty(message) || message.Length > 256) throw new ArgumentException(Translations.ish_chat_length);
            if (message.StartsWith("/", StringComparison.Ordinal))
            {
                send(0x06, types.GetString(message.Substring(1)));
                return;
            }
            long timestamp = (DateTime.UtcNow.Ticks - new DateTime(1970, 1, 1).Ticks) / TimeSpan.TicksPerMillisecond;
            send(0x08, types.ConcatBytes(types.GetString(message), types.GetLong(timestamp), types.GetLong(0),
                new byte[] { 0, 0, 0, 0, 0, 0 })); // No signature, zero offset, empty 20-bit last-seen window, checksum zero.
        }

        public bool Handle(int id, byte[] payload)
        {
            var data = new Queue<byte>(payload);
            try
            {
                switch (id)
                {
                    case 0x3F: // Player Chat, including 1.21.5+ global index.
                        types.ReadNextVarInt(data); // Global index.
                        Guid player = types.ReadNextUUID(data);
                        types.ReadNextVarInt(data); // Sender's chain index.
                        byte[] signature = ReadBoolean(data) ? types.ReadData(256, data) : null;
                        string body = ReadString(data);
                        Require(body.Length <= 256);
                        types.ReadNextLong(data); // Timestamp.
                        types.ReadNextLong(data); // Salt.
                        int previous = types.ReadNextVarInt(data);
                        Require(previous >= 0 && previous <= 20);
                        for (int index = 0; index < previous; index++)
                        {
                            int reference = types.ReadNextVarInt(data);
                            Require(reference >= 0);
                            if (reference == 0) types.ReadData(256, data);
                        }
                        string decorated = ReadBoolean(data) ? types.ReadNextChat(data) : null;
                        int filter = types.ReadNextVarInt(data);
                        Require(filter >= 0 && filter <= 2);
                        if (filter == 2)
                        {
                            int maskWords = types.ReadNextVarInt(data);
                            Require(maskWords >= 0 && maskWords <= 4);
                            types.ReadData(maskWords * 8, data);
                        }
                        int holder = types.ReadNextVarInt(data);
                        Require(holder >= 0);
                        if (holder == 0) { SkipChatDecoration(data); SkipChatDecoration(data); }
                        string displayName = types.ReadNextChat(data);
                        if (ReadBoolean(data)) types.ReadNextChat(data); // Target display name.
                        Require(data.Count == 0);
                        LastPlayerId = player;
                        LastPlayerSender = displayName;
                        LastPlayerMessageFiltered = filter != 0;
                        LastPlayerMessage = filter == 0 ? decorated ?? body : string.Empty;
                        LastPlayerSignaturePresent = signature != null;
                        if (signature != null)
                        {
                            string signatureId = Convert.ToBase64String(signature);
                            if (!acknowledgedSignatures.Contains(signatureId))
                            {
                                // Delivery acknowledgement is not cryptographic verification.
                                send(0x05, types.GetVarInt(1));
                                acknowledgedSignatures.Enqueue(signatureId);
                                if (acknowledgedSignatures.Count > 20) acknowledgedSignatures.Dequeue();
                            }
                        }
                        return true;
                    case 0x21: // Disguised/profileless chat, including /say.
                        string serverMessage = types.ReadNextChat(data);
                        int chatType = types.ReadNextVarInt(data);
                        Require(chatType >= 0);
                        if (chatType == 0)
                        {
                            SkipChatDecoration(data);
                            SkipChatDecoration(data); // Narration.
                        }
                        string sender = types.ReadNextChat(data);
                        if (ReadBoolean(data)) types.ReadNextChat(data); // Target.
                        Require(data.Count == 0);
                        LastSystemMessage = serverMessage;
                        LastServerSender = sender;
                        LastMessageIsOverlay = false;
                        return true;
                    case 0x30: // ClientboundLoginPacket / CommonPlayerSpawnInfo, official 1.21.11.
                        int entityId = types.ReadNextInt(data);
                        ReadBoolean(data); // Hardcore.
                        int worlds = types.ReadNextVarInt(data);
                        Require(worlds >= 0 && worlds <= 1024);
                        for (int index = 0; index < worlds; index++) ReadString(data);
                        types.ReadNextVarInt(data); // Max players.
                        types.ReadNextVarInt(data); // View distance.
                        types.ReadNextVarInt(data); // Simulation distance.
                        ReadBoolean(data); // Reduced debug.
                        ReadBoolean(data); // Show death screen.
                        ReadBoolean(data); // Limited crafting.
                        types.ReadNextVarInt(data); // Dimension type registry reference.
                        string dimension = ReadString(data);
                        types.ReadNextLong(data); // Seed.
                        types.ReadNextByte(data); // Game mode.
                        types.ReadNextByte(data); // Previous game mode.
                        ReadBoolean(data); // Debug world.
                        ReadBoolean(data); // Flat world.
                        if (ReadBoolean(data))
                        {
                            ReadString(data); // Last death dimension.
                            types.ReadNextLong(data); // Packed block position.
                        }
                        types.ReadNextVarInt(data); // Portal cooldown.
                        int seaLevel = types.ReadNextVarInt(data);
                        bool secure = ReadBoolean(data);
                        Require(data.Count == 0);
                        EntityId = entityId;
                        DimensionName = dimension;
                        SeaLevel = seaLevel;
                        EnforcesSecureChat = secure;
                        Joined = true;
                        send(0x2B, new byte[0]); // Player Loaded.
                        return true;
                    case 0x2B: // Keep alive.
                        Require(payload.Length == 8);
                        send(0x1B, payload);
                        return true;
                    case 0x3B: // Ping.
                        Require(payload.Length == 4);
                        send(0x2C, payload);
                        return true;
                    case 0x77: // System chat.
                        string message = types.ReadNextChat(data);
                        Require(data.Count == 1);
                        byte overlay = data.Dequeue();
                        Require(overlay <= 1);
                        LastSystemMessage = message;
                        LastMessageIsOverlay = overlay != 0;
                        return true;
                    case 0x20: // Disconnect component.
                        DisconnectReason = types.ReadNextChat(data);
                        Require(data.Count == 0);
                        return true;
                    case 0x46: // Synchronize player position (1.21.2+ format).
                        int teleport = types.ReadNextVarInt(data);
                        double px = types.ReadNextDouble(data), py = types.ReadNextDouble(data), pz = types.ReadNextDouble(data);
                        types.ReadNextDouble(data); // Velocity X.
                        types.ReadNextDouble(data); // Velocity Y.
                        types.ReadNextDouble(data); // Velocity Z.
                        float ry = types.ReadNextFloat(data), rp = types.ReadNextFloat(data);
                        int flags = types.ReadNextInt(data);
                        Require(data.Count == 0 && teleport >= 0);
                        x = (flags & 1) != 0 ? x + px : px;
                        y = (flags & 2) != 0 ? y + py : py;
                        z = (flags & 4) != 0 ? z + pz : pz;
                        yaw = (flags & 8) != 0 ? yaw + ry : ry;
                        pitch = (flags & 16) != 0 ? pitch + rp : rp;
                        Require(!double.IsNaN(x) && !double.IsInfinity(x) && !double.IsNaN(y) && !double.IsInfinity(y) &&
                            !double.IsNaN(z) && !double.IsInfinity(z) && !float.IsNaN(yaw) && !float.IsInfinity(yaw) &&
                            !float.IsNaN(pitch) && !float.IsInfinity(pitch));
                        send(0x00, types.GetVarInt(teleport));
                        send(0x1E, types.ConcatBytes(types.GetDouble(x), types.GetDouble(y), types.GetDouble(z),
                            types.GetFloat(yaw), types.GetFloat(pitch), new byte[] { 0 }));
                        return true;
                    default: return false;
                }
            }
            catch (InvalidOperationException) { throw new InvalidDataException(Translations.ish_packet_invalid); }
        }

        private static void Require(bool condition)
        {
            if (!condition) throw new InvalidDataException(Translations.ish_packet_invalid);
        }

        private bool ReadBoolean(Queue<byte> data)
        {
            byte value = types.ReadNextByte(data);
            Require(value <= 1);
            return value != 0;
        }

        private string ReadString(Queue<byte> data)
        {
            int length = types.ReadNextVarInt(data);
            Require(length >= 0 && length <= 131068 && length <= data.Count);
            return System.Text.Encoding.UTF8.GetString(types.ReadData(length, data));
        }

        private void SkipChatDecoration(Queue<byte> data)
        {
            ReadString(data); // Translation key.
            int count = types.ReadNextVarInt(data);
            Require(count >= 0 && count <= 3);
            for (int index = 0; index < count; index++)
            {
                int parameter = types.ReadNextVarInt(data);
                Require(parameter >= 0 && parameter <= 2);
            }
            if (data.Count > 0 && data.Peek() == 0) data.Dequeue();
            else NetworkText12111.Read(data); // Style NBT.
        }
    }
}
