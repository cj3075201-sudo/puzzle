using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;

namespace OUAT.Jigsaw
{
    /// <summary>Kind of a parsed JSON value.</summary>
    public enum JsonKind
    {
        /// <summary>JSON <c>null</c>.</summary>
        Null,
        /// <summary>JSON <c>true</c> or <c>false</c>.</summary>
        Bool,
        /// <summary>JSON number (stored as <see cref="double"/>).</summary>
        Number,
        /// <summary>JSON string.</summary>
        String,
        /// <summary>JSON array.</summary>
        Array,
        /// <summary>JSON object (keys keep insertion order).</summary>
        Object,
    }

    /// <summary>
    /// Immutable JSON value produced by <see cref="MiniJson.ParseNode"/>.
    /// Small self-contained replacement for Unity's JsonUtility, which cannot read
    /// heterogeneous arrays such as <c>["E","tab","round"]</c> or nested spec trees.
    /// </summary>
    public abstract class JsonNode
    {
        /// <summary>The kind of this value.</summary>
        public abstract JsonKind Kind { get; }

        /// <summary>
        /// JavaScript truthiness of this value (<c>null</c>, <c>false</c>, <c>0</c> and <c>""</c> are falsy).
        /// Used where the original core.js relies on <c>!value</c>.
        /// </summary>
        public virtual bool IsTruthy => true;

        /// <summary>Returns the string value, or <c>null</c> when this is not a string.</summary>
        public string AsString => this is JsonString s ? s.Value : null;

        /// <summary>Returns this value as an array, or <c>null</c> when it is not an array.</summary>
        public JsonArray AsArray => this as JsonArray;

        /// <summary>Returns this value as an object, or <c>null</c> when it is not an object.</summary>
        public JsonObject AsObject => this as JsonObject;
    }

    /// <summary>JSON <c>null</c>.</summary>
    public sealed class JsonNull : JsonNode
    {
        /// <summary>Shared instance.</summary>
        public static readonly JsonNull Instance = new JsonNull();
        private JsonNull() { }
        /// <inheritdoc/>
        public override JsonKind Kind => JsonKind.Null;
        /// <inheritdoc/>
        public override bool IsTruthy => false;
    }

    /// <summary>JSON boolean.</summary>
    public sealed class JsonBool : JsonNode
    {
        /// <summary>Shared <c>true</c>.</summary>
        public static readonly JsonBool True = new JsonBool(true);
        /// <summary>Shared <c>false</c>.</summary>
        public static readonly JsonBool False = new JsonBool(false);
        private JsonBool(bool value) { Value = value; }
        /// <summary>The boolean value.</summary>
        public bool Value { get; }
        /// <inheritdoc/>
        public override JsonKind Kind => JsonKind.Bool;
        /// <inheritdoc/>
        public override bool IsTruthy => Value;
    }

    /// <summary>JSON number.</summary>
    public sealed class JsonNumber : JsonNode
    {
        /// <summary>Creates a number node.</summary>
        public JsonNumber(double value) { Value = value; }
        /// <summary>The numeric value.</summary>
        public double Value { get; }
        /// <inheritdoc/>
        public override JsonKind Kind => JsonKind.Number;
        /// <inheritdoc/>
        public override bool IsTruthy => Value != 0 && !double.IsNaN(Value);
    }

    /// <summary>JSON string.</summary>
    public sealed class JsonString : JsonNode
    {
        /// <summary>Creates a string node.</summary>
        public JsonString(string value) { Value = value ?? throw new ArgumentNullException(nameof(value)); }
        /// <summary>The string value (UTF-16, lone surrogates preserved).</summary>
        public string Value { get; }
        /// <inheritdoc/>
        public override JsonKind Kind => JsonKind.String;
        /// <inheritdoc/>
        public override bool IsTruthy => Value.Length > 0;
    }

    /// <summary>JSON array.</summary>
    public sealed class JsonArray : JsonNode
    {
        private readonly List<JsonNode> items;
        /// <summary>Creates an array node.</summary>
        public JsonArray(IEnumerable<JsonNode> items) { this.items = new List<JsonNode>(items); }
        /// <summary>The elements.</summary>
        public IReadOnlyList<JsonNode> Items => items;
        /// <summary>Number of elements.</summary>
        public int Count => items.Count;
        /// <summary>Element at <paramref name="index"/>.</summary>
        public JsonNode this[int index] => items[index];
        /// <inheritdoc/>
        public override JsonKind Kind => JsonKind.Array;
    }

    /// <summary>JSON object. Keys keep first-insertion order; a repeated key replaces the value in place (like <c>JSON.parse</c>).</summary>
    public sealed class JsonObject : JsonNode
    {
        private readonly List<string> keys = new List<string>();
        private readonly Dictionary<string, JsonNode> values = new Dictionary<string, JsonNode>(StringComparer.Ordinal);

        /// <summary>Creates an empty object node.</summary>
        public JsonObject() { }

        /// <summary>Keys in insertion order.</summary>
        public IReadOnlyList<string> Keys => keys;

        /// <summary>Number of members.</summary>
        public int Count => keys.Count;

        /// <summary>Sets a member. An existing key keeps its position.</summary>
        public void Set(string key, JsonNode value)
        {
            if (key == null) throw new ArgumentNullException(nameof(key));
            if (!values.ContainsKey(key)) keys.Add(key);
            values[key] = value ?? JsonNull.Instance;
        }

        /// <summary>Gets a member, or <c>null</c> (C# null, not <see cref="JsonNull"/>) when absent.</summary>
        public JsonNode Get(string key) => key != null && values.TryGetValue(key, out var v) ? v : null;

        /// <summary>True when the key is present.</summary>
        public bool Has(string key) => key != null && values.ContainsKey(key);

        /// <inheritdoc/>
        public override JsonKind Kind => JsonKind.Object;
    }

    /// <summary>Strict RFC 8259 JSON reader plus a <c>JSON.stringify</c>-compatible string quoter.</summary>
    public static class MiniJson
    {
        private const int MaxDepth = 512;

        private const char ByteOrderMark = (char)0xFEFF;

        /// <summary>
        /// Parses JSON text into plain CLR values: <c>Dictionary&lt;string,object&gt;</c>, <c>List&lt;object&gt;</c>,
        /// <see cref="string"/>, <see cref="double"/>, <see cref="bool"/> or <c>null</c>.
        /// A single leading byte-order mark is ignored (Node's <c>require</c> of a .json file does the same).
        /// Use <see cref="ParseNode"/> when object key order matters (model tables).
        /// </summary>
        /// <exception cref="FormatException">The text is not valid JSON.</exception>
        public static object Parse(string json) => ToPlain(ParseNode(json));

        /// <summary>
        /// Parses JSON text into <see cref="JsonNode"/> values (objects keep key order, as in JavaScript).
        /// A single leading byte-order mark is ignored.
        /// </summary>
        /// <exception cref="FormatException">The text is not valid JSON.</exception>
        public static JsonNode ParseNode(string json)
        {
            if (json == null) throw new ArgumentNullException(nameof(json));
            var reader = new Reader(json);
            if (json.Length > 0 && json[0] == ByteOrderMark) reader.Pos = 1;
            reader.SkipWhitespace();
            var node = reader.ReadValue(0);
            reader.SkipWhitespace();
            if (reader.Pos != json.Length) throw reader.Error("unexpected trailing characters");
            return node;
        }

        /// <summary>Converts a node to the plain CLR form returned by <see cref="Parse"/>.</summary>
        public static object ToPlain(JsonNode node)
        {
            switch (node)
            {
                case null: return null;
                case JsonString s: return s.Value;
                case JsonNumber n: return n.Value;
                case JsonBool b: return b.Value;
                case JsonArray a: return a.Items.Select(ToPlain).ToList();
                case JsonObject o:
                    var d = new Dictionary<string, object>(StringComparer.Ordinal);
                    foreach (var k in o.Keys) d[k] = ToPlain(o.Get(k));
                    return d;
                default: return null; // JsonNull
            }
        }

        /// <summary>
        /// JavaScript truthiness of a plain or node value: <c>null</c>, <c>false</c>, <c>0</c>, <c>NaN</c> and <c>""</c> are falsy.
        /// </summary>
        public static bool IsTruthy(object value)
        {
            switch (value)
            {
                case null: return false;
                case JsonNode n: return n.IsTruthy;
                case bool b: return b;
                case string s: return s.Length > 0;
                case double d: return d != 0 && !double.IsNaN(d);
                case float f: return f != 0 && !float.IsNaN(f);
                case int i: return i != 0;
                case long l: return l != 0;
                default: return true;
            }
        }

        /// <summary>
        /// Quotes a string exactly like JavaScript's <c>JSON.stringify(string)</c> (well-formed variant, ES2019+):
        /// escapes <c>"</c>, <c>\</c>, control characters and lone surrogates; leaves all other characters as is.
        /// </summary>
        public static string Quote(string value)
        {
            var sb = new StringBuilder(value.Length + 2);
            AppendQuoted(sb, value);
            return sb.ToString();
        }

        /// <summary>Appends <see cref="Quote"/> output to a builder.</summary>
        public static void AppendQuoted(StringBuilder sb, string value)
        {
            sb.Append('"');
            for (int i = 0; i < value.Length; i++)
            {
                char c = value[i];
                switch (c)
                {
                    case '"': sb.Append("\\\""); continue;
                    case '\\': sb.Append("\\\\"); continue;
                    case '\b': sb.Append("\\b"); continue;
                    case '\f': sb.Append("\\f"); continue;
                    case '\n': sb.Append("\\n"); continue;
                    case '\r': sb.Append("\\r"); continue;
                    case '\t': sb.Append("\\t"); continue;
                }
                if (c < 0x20)
                {
                    AppendUnicodeEscape(sb, c);
                }
                else if (char.IsHighSurrogate(c))
                {
                    if (i + 1 < value.Length && char.IsLowSurrogate(value[i + 1])) { sb.Append(c).Append(value[i + 1]); i++; }
                    else AppendUnicodeEscape(sb, c);
                }
                else if (char.IsLowSurrogate(c))
                {
                    AppendUnicodeEscape(sb, c);
                }
                else sb.Append(c);
            }
            sb.Append('"');
        }

        private static void AppendUnicodeEscape(StringBuilder sb, char c)
        {
            sb.Append("\\u").Append(((int)c).ToString("x4", CultureInfo.InvariantCulture));
        }

        private sealed class Reader
        {
            private readonly string s;
            public int Pos;

            public Reader(string s) { this.s = s; }

            public FormatException Error(string what) => new FormatException($"Invalid JSON at {Pos}: {what}.");

            public void SkipWhitespace()
            {
                while (Pos < s.Length)
                {
                    char c = s[Pos];
                    if (c == ' ' || c == '\t' || c == '\n' || c == '\r') Pos++;
                    else break;
                }
            }

            public JsonNode ReadValue(int depth)
            {
                if (depth > MaxDepth) throw Error("nesting too deep");
                if (Pos >= s.Length) throw Error("unexpected end");
                char c = s[Pos];
                switch (c)
                {
                    case '{': return ReadObject(depth);
                    case '[': return ReadArray(depth);
                    case '"': return new JsonString(ReadString());
                    case 't': Expect("true"); return JsonBool.True;
                    case 'f': Expect("false"); return JsonBool.False;
                    case 'n': Expect("null"); return JsonNull.Instance;
                    default:
                        if (c == '-' || (c >= '0' && c <= '9')) return ReadNumber();
                        throw Error($"unexpected character '{c}'");
                }
            }

            private void Expect(string literal)
            {
                if (string.CompareOrdinal(s, Pos, literal, 0, literal.Length) != 0) throw Error($"expected '{literal}'");
                Pos += literal.Length;
            }

            private JsonObject ReadObject(int depth)
            {
                var obj = new JsonObject();
                Pos++; // {
                SkipWhitespace();
                if (Pos < s.Length && s[Pos] == '}') { Pos++; return obj; }
                while (true)
                {
                    SkipWhitespace();
                    if (Pos >= s.Length || s[Pos] != '"') throw Error("expected object key");
                    string key = ReadString();
                    SkipWhitespace();
                    if (Pos >= s.Length || s[Pos] != ':') throw Error("expected ':'");
                    Pos++;
                    SkipWhitespace();
                    obj.Set(key, ReadValue(depth + 1));
                    SkipWhitespace();
                    if (Pos >= s.Length) throw Error("unexpected end in object");
                    if (s[Pos] == ',') { Pos++; continue; }
                    if (s[Pos] == '}') { Pos++; return obj; }
                    throw Error("expected ',' or '}'");
                }
            }

            private JsonArray ReadArray(int depth)
            {
                var items = new List<JsonNode>();
                Pos++; // [
                SkipWhitespace();
                if (Pos < s.Length && s[Pos] == ']') { Pos++; return new JsonArray(items); }
                while (true)
                {
                    SkipWhitespace();
                    items.Add(ReadValue(depth + 1));
                    SkipWhitespace();
                    if (Pos >= s.Length) throw Error("unexpected end in array");
                    if (s[Pos] == ',') { Pos++; continue; }
                    if (s[Pos] == ']') { Pos++; return new JsonArray(items); }
                    throw Error("expected ',' or ']'");
                }
            }

            private string ReadString()
            {
                Pos++; // opening quote
                var sb = new StringBuilder();
                while (true)
                {
                    if (Pos >= s.Length) throw Error("unterminated string");
                    char c = s[Pos++];
                    if (c == '"') return sb.ToString();
                    if (c < 0x20) throw Error("control character in string");
                    if (c != '\\') { sb.Append(c); continue; }
                    if (Pos >= s.Length) throw Error("unterminated escape");
                    char e = s[Pos++];
                    switch (e)
                    {
                        case '"': sb.Append('"'); break;
                        case '\\': sb.Append('\\'); break;
                        case '/': sb.Append('/'); break;
                        case 'b': sb.Append('\b'); break;
                        case 'f': sb.Append('\f'); break;
                        case 'n': sb.Append('\n'); break;
                        case 'r': sb.Append('\r'); break;
                        case 't': sb.Append('\t'); break;
                        case 'u':
                            if (Pos + 4 > s.Length) throw Error("short unicode escape");
                            int code = 0;
                            for (int k = 0; k < 4; k++)
                            {
                                int h = HexValue(s[Pos + k]);
                                if (h < 0) throw Error("bad unicode escape");
                                code = (code << 4) | h;
                            }
                            Pos += 4;
                            sb.Append((char)code);
                            break;
                        default: throw Error($"bad escape '\\{e}'");
                    }
                }
            }

            private static int HexValue(char c)
            {
                if (c >= '0' && c <= '9') return c - '0';
                if (c >= 'a' && c <= 'f') return c - 'a' + 10;
                if (c >= 'A' && c <= 'F') return c - 'A' + 10;
                return -1;
            }

            private JsonNumber ReadNumber()
            {
                int start = Pos;
                if (s[Pos] == '-') Pos++;
                if (Pos >= s.Length) throw Error("bad number");
                if (s[Pos] == '0') Pos++;
                else if (s[Pos] >= '1' && s[Pos] <= '9') { while (Pos < s.Length && s[Pos] >= '0' && s[Pos] <= '9') Pos++; }
                else throw Error("bad number");
                if (Pos < s.Length && s[Pos] == '.')
                {
                    Pos++;
                    int digits = Pos;
                    while (Pos < s.Length && s[Pos] >= '0' && s[Pos] <= '9') Pos++;
                    if (Pos == digits) throw Error("bad fraction");
                }
                if (Pos < s.Length && (s[Pos] == 'e' || s[Pos] == 'E'))
                {
                    Pos++;
                    if (Pos < s.Length && (s[Pos] == '+' || s[Pos] == '-')) Pos++;
                    int digits = Pos;
                    while (Pos < s.Length && s[Pos] >= '0' && s[Pos] <= '9') Pos++;
                    if (Pos == digits) throw Error("bad exponent");
                }
                var text = s.Substring(start, Pos - start);
                return new JsonNumber(double.Parse(text, NumberStyles.Float, CultureInfo.InvariantCulture));
            }
        }
    }
}
