using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net.Sockets;
using MinecraftClient.Crypto;

namespace MinecraftClient.Protocol.Handlers
{
    /// <summary>Protocol-774 transport/login/configuration. Play handling is not provided here.</summary>
    public sealed class ModernSession12111 : IDisposable
    {
        private readonly SocketWrapper socket;
        private readonly DataTypes types = new DataTypes(774);
        private int compression = -1;
        public bool ConfigurationFinished { get; private set; }
        public event Action<int, byte[]> ConfigurationData;

        public ModernSession12111(TcpClient client)
        {
            if (client == null) throw new ArgumentNullException("client");
            socket = new SocketWrapper(client);
        }

        public void Send(int id, byte[] payload)
        {
            byte[] body = types.GetVarInt(id).Concat(payload).ToArray();
            if (body.Length > ZlibUtils.MaximumPacketSize) throw Invalid();
            if (compression >= 0)
                body = body.Length >= compression
                    ? types.GetVarInt(body.Length).Concat(ZlibUtils.Compress(body)).ToArray()
                    : new byte[] { 0 }.Concat(body).ToArray();
            socket.SendDataRAW(types.GetVarInt(body.Length).Concat(body).ToArray());
        }

        public byte[] Read(out int id)
        {
            int length = types.ReadNextVarIntRAW(socket);
            if (length <= 0 || length > ZlibUtils.MaximumPacketSize) throw Invalid();
            var body = new Queue<byte>(socket.ReadDataRAW(length));
            if (compression >= 0)
            {
                int expanded = types.ReadNextVarInt(body);
                if (expanded < 0 || expanded > ZlibUtils.MaximumPacketSize) throw Invalid();
                if (expanded != 0)
                {
                    if (expanded < compression) throw Invalid();
                    body = new Queue<byte>(ZlibUtils.Decompress(body.ToArray(), expanded));
                }
            }
            if (body.Count == 0) throw Invalid();
            id = types.ReadNextVarInt(body);
            return body.ToArray();
        }

        public void Login(string host, ushort port, string username, Guid uuid, string accessToken)
        {
            if (ConfigurationFinished) throw new InvalidOperationException(Translations.ish_configuration_finished);
            var login = new Login12111();
            Send(0, types.ConcatBytes(types.GetVarInt(774), types.GetString(host), types.GetUShort(port), new byte[] { 2 }));
            Send(0, login.CreateStart(username, uuid));
            while (!login.Acknowledged)
            {
                int id;
                var payload = new Queue<byte>(Read(out id));
                switch (id)
                {
                    case 0: throw new IOException(ChatParser.ParseText(types.ReadNextString(payload)));
                    case 1:
                        string serverId = types.ReadNextString(payload);
                        byte[] key = types.ReadNextByteArray(payload);
                        byte[] challenge = types.ReadNextByteArray(payload);
                        bool authenticate = types.ReadNextBool(payload);
                        if (payload.Count != 0) throw Invalid();
                        byte[] secret = CryptoHandler.GenerateAESPrivateKey();
                        if (authenticate && (string.IsNullOrEmpty(accessToken) ||
                            !ProtocolHandler.SessionCheck(uuid.ToString("N"), accessToken, CryptoHandler.getServerHash(serverId, key, secret))))
                            throw new IOException(Translations.Get("mcc.session_fail"));
                        using (var rsa = CryptoHandler.DecodeRSAPublicKey(key))
                            Send(1, types.ConcatBytes(types.GetArray(rsa.Encrypt(secret, false)), types.GetArray(rsa.Encrypt(challenge, false))));
                        socket.SwitchToEncrypted(secret);
                        break;
                    case 2: Send(3, login.AcceptSuccess(payload)); break;
                    case 3:
                        compression = types.ReadNextVarInt(payload);
                        if (compression < 0 || payload.Count != 0) throw Invalid();
                        break;
                    case 4: Send(2, login.DeclinePlugin(payload)); break;
                    case 5:
                        string cookie = types.ReadNextString(payload);
                        if (payload.Count != 0) throw Invalid();
                        Send(4, types.GetString(cookie).Concat(new byte[] { 0 }).ToArray());
                        break;
                    default: throw Invalid();
                }
            }
            Send(0, Play12111.ClientInformation());
            var configuration = new Configuration12111();
            while (!configuration.Finished)
            {
                int id;
                byte[] payload = Read(out id);
                if (id == 2) throw new IOException(ChatParser.ParseNetworkText(new Queue<byte>(payload)));
                int replyId;
                byte[] reply;
                if (configuration.TryReply(id, payload, out replyId, out reply)) Send(replyId, reply);
                else
                {
                    // These require explicit user/session policy; do not auto-accept.
                    if (id == 9 || id == 11 || id == 19)
                        throw new NotSupportedException(Translations.ish_configuration_policy);
                    var callback = ConfigurationData;
                    if (callback != null) callback(id, payload);
                }
            }
            ConfigurationFinished = true;
        }

        public void Dispose() { socket.Disconnect(); }
        private static InvalidDataException Invalid() { return new InvalidDataException(Translations.ish_packet_invalid); }
    }
}
