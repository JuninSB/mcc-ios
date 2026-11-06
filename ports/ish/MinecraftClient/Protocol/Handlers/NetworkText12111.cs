using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;

namespace MinecraftClient.Protocol.Handlers
{
    /// <summary>Unnamed network NBT used by modern text components, with bounded parsing.</summary>
    public static class NetworkText12111
    {
        public static Json.JSONData Read(Queue<byte> input)
        {
            if (input == null) throw new ArgumentNullException("input");
            int budget = 8192;
            try { return ReadTag(input, Take(input), 0, ref budget); }
            catch (InvalidOperationException) { throw Invalid(); }
        }

        private static Json.JSONData ReadTag(Queue<byte> input, int type, int depth, ref int budget)
        {
            if (depth > 64 || --budget < 0) throw Invalid();
            if (type == 10)
            {
                var result = new Json.JSONData(Json.JSONData.DataType.Object);
                int child;
                while ((child = Take(input)) != 0)
                {
                    string name = ReadString(input);
                    result.Properties[name] = ReadTag(input, child, depth + 1, ref budget);
                }
                return result;
            }
            if (type == 9 || type == 7 || type == 11 || type == 12)
            {
                int child = type == 9 ? Take(input) : type == 7 ? 1 : type == 11 ? 3 : 4;
                int count = unchecked((int)ReadInteger(input, 4));
                if (count < 0 || count > budget || (count > 0 && (child < 1 || child > 12))) throw Invalid();
                var result = new Json.JSONData(Json.JSONData.DataType.Array);
                for (int index = 0; index < count; index++) result.DataArray.Add(ReadTag(input, child, depth + 1, ref budget));
                return result;
            }
            string value;
            switch (type)
            {
                case 1: value = unchecked((sbyte)Take(input)).ToString(CultureInfo.InvariantCulture); break;
                case 2: value = unchecked((short)ReadInteger(input, 2)).ToString(CultureInfo.InvariantCulture); break;
                case 3: value = unchecked((int)ReadInteger(input, 4)).ToString(CultureInfo.InvariantCulture); break;
                case 4: value = ReadInteger(input, 8).ToString(CultureInfo.InvariantCulture); break;
                case 5:
                case 6:
                    int size = type == 5 ? 4 : 8;
                    byte[] number = ReadBytes(input, size);
                    if (BitConverter.IsLittleEndian) Array.Reverse(number);
                    value = type == 5 ? BitConverter.ToSingle(number, 0).ToString(CultureInfo.InvariantCulture)
                        : BitConverter.ToDouble(number, 0).ToString(CultureInfo.InvariantCulture);
                    break;
                case 8: value = ReadString(input); break;
                default: throw Invalid();
            }
            return new Json.JSONData(Json.JSONData.DataType.String) { StringValue = value };
        }

        private static byte Take(Queue<byte> input)
        {
            if (input.Count == 0) throw Invalid();
            return input.Dequeue();
        }

        private static long ReadInteger(Queue<byte> input, int size)
        {
            long result = 0;
            for (int index = 0; index < size; index++) result = unchecked((result << 8) | Take(input));
            return result;
        }

        private static byte[] ReadBytes(Queue<byte> input, int length)
        {
            if (length < 0 || length > input.Count) throw Invalid();
            var bytes = new byte[length];
            for (int index = 0; index < length; index++) bytes[index] = input.Dequeue();
            return bytes;
        }

        private static string ReadString(Queue<byte> input)
        {
            int length = (int)ReadInteger(input, 2);
            return Encoding.UTF8.GetString(ReadBytes(input, length));
        }

        private static InvalidDataException Invalid()
        {
            return new InvalidDataException(Translations.ish_packet_invalid);
        }
    }
}
