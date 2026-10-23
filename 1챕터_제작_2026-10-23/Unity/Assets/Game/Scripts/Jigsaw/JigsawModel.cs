using System;
using System.Collections.Generic;
using System.Linq;

namespace OUAT.Jigsaw
{
    /// <summary>Cell side. Declaration order (N, E, S, W) matches <c>Object.keys(DIR)</c> in core.js.</summary>
    public enum Side
    {
        /// <summary>Up (y - 1).</summary>
        N = 0,
        /// <summary>Right (x + 1).</summary>
        E = 1,
        /// <summary>Down (y + 1).</summary>
        S = 2,
        /// <summary>Left (x - 1).</summary>
        W = 3,
    }

    /// <summary>Port kind: a tab (돌출) sticks out, a socket (홈) receives a tab.</summary>
    public enum PortKind
    {
        /// <summary>Tab (<c>"tab"</c>). A joint reads from the tab side to the socket side.</summary>
        Tab,
        /// <summary>Socket (<c>"socket"</c>).</summary>
        Socket,
    }

    /// <summary>Joint profile. A tab only fits a socket of the same profile.</summary>
    public enum PortProfile
    {
        /// <summary>Ordinary round joint (<c>"round"</c>).</summary>
        Round,
        /// <summary>Twin joint used by the marked-subject models (<c>"twin"</c>).</summary>
        Twin,
    }

    /// <summary>Helpers for <see cref="Side"/>, mirroring the <c>DIR</c> table of core.js.</summary>
    public static class Sides
    {
        /// <summary>All sides in core.js <c>Object.keys(DIR)</c> order: N, E, S, W.</summary>
        public static readonly IReadOnlyList<Side> All = new[] { Side.N, Side.E, Side.S, Side.W };

        /// <summary>Column offset of the neighbour on this side.</summary>
        public static int Dx(this Side side) => side == Side.E ? 1 : side == Side.W ? -1 : 0;

        /// <summary>Row offset of the neighbour on this side (y grows downwards).</summary>
        public static int Dy(this Side side) => side == Side.S ? 1 : side == Side.N ? -1 : 0;

        /// <summary>The facing side of the neighbour.</summary>
        public static Side Opposite(this Side side) => (Side)(((int)side + 2) % 4);

        /// <summary>Data code (<c>"N"</c>, <c>"E"</c>, <c>"S"</c>, <c>"W"</c>).</summary>
        public static string Code(this Side side) => side.ToString();

        /// <summary>Parses a data code. Returns false for anything but the four exact codes.</summary>
        public static bool TryParse(string code, out Side side)
        {
            switch (code)
            {
                case "N": side = Side.N; return true;
                case "E": side = Side.E; return true;
                case "S": side = Side.S; return true;
                case "W": side = Side.W; return true;
                default: side = Side.N; return false;
            }
        }
    }

    /// <summary>One port of a model: which side, tab or socket, and the profile.</summary>
    public readonly struct Port : IEquatable<Port>
    {
        /// <summary>Creates a port.</summary>
        public Port(Side side, PortKind kind, PortProfile profile)
        {
            Side = side;
            Kind = kind;
            Profile = profile;
        }

        /// <summary>Side of the cell the port is on.</summary>
        public Side Side { get; }
        /// <summary>Tab or socket.</summary>
        public PortKind Kind { get; }
        /// <summary>Joint profile.</summary>
        public PortProfile Profile { get; }

        /// <summary>Data code of the kind (<c>"tab"</c> / <c>"socket"</c>).</summary>
        public static string KindCode(PortKind kind) => kind == PortKind.Tab ? "tab" : "socket";

        /// <summary>Data code of the profile (<c>"round"</c> / <c>"twin"</c>).</summary>
        public static string ProfileCode(PortProfile profile) => profile == PortProfile.Round ? "round" : "twin";

        /// <summary>Parses a kind code; false for anything but <c>"tab"</c> / <c>"socket"</c>.</summary>
        public static bool TryParseKind(string code, out PortKind kind)
        {
            if (code == "tab") { kind = PortKind.Tab; return true; }
            if (code == "socket") { kind = PortKind.Socket; return true; }
            kind = PortKind.Tab;
            return false;
        }

        /// <summary>Parses a profile code; false for anything but <c>"round"</c> / <c>"twin"</c>.</summary>
        public static bool TryParseProfile(string code, out PortProfile profile)
        {
            if (code == "round") { profile = PortProfile.Round; return true; }
            if (code == "twin") { profile = PortProfile.Twin; return true; }
            profile = PortProfile.Round;
            return false;
        }

        /// <summary>True when this port and <paramref name="other"/> (on facing sides) form a joint: one tab, one socket, same profile.</summary>
        public bool Fits(Port other) => Kind != other.Kind && Profile == other.Profile;

        /// <summary>Signature form used by core.js <c>signature</c>: <c>"E:tab:round"</c>.</summary>
        public override string ToString() => Side.Code() + ":" + KindCode(Kind) + ":" + ProfileCode(Profile);

        /// <inheritdoc/>
        public bool Equals(Port other) => Side == other.Side && Kind == other.Kind && Profile == other.Profile;
        /// <inheritdoc/>
        public override bool Equals(object obj) => obj is Port p && Equals(p);
        /// <inheritdoc/>
        public override int GetHashCode() => ((int)Side * 4 + (int)Kind) * 4 + (int)Profile;
    }

    /// <summary>
    /// A colourless jigsaw model (모형): its ports and outline. Colour comes from the word put into it, not from the model.
    /// </summary>
    public sealed class JigsawModel
    {
        private static readonly string[] ValidColors = { "none", "yellow", "blue" };

        private readonly Port?[] portBySide; // null array = ports are malformed (core.js portMap returned null)

        /// <summary>Creates a well-formed model from code (colour <c>"none"</c>). Socket sides are derived from the ports.</summary>
        /// <exception cref="ArgumentException">Two ports share a side.</exception>
        public JigsawModel(string id, IEnumerable<Port> ports, string path = null)
            : this(id, "none", true, ToRaw(ports), null, path)
        {
            if (portBySide == null) throw new ArgumentException("Two ports share a side.", nameof(ports));
        }

        private JigsawModel(string id, string color, bool portsIsArray, IReadOnlyList<string[]> rawPorts,
            IReadOnlyList<string> socketSides, string path)
        {
            Id = id ?? throw new ArgumentNullException(nameof(id));
            Color = color;
            Path = path;
            IsValidModel = color != null && Array.IndexOf(ValidColors, color) >= 0 && portsIsArray;

            var ports = new List<Port>();
            var bySide = new Port?[4];
            bool wellFormed = portsIsArray;
            bool signatureOk = portsIsArray;
            var signatureParts = new List<string>();
            foreach (var raw in rawPorts ?? Array.Empty<string[]>())
            {
                if (raw == null) { wellFormed = false; signatureOk = false; continue; }
                if (raw.Any(e => e == null)) signatureOk = false;
                else signatureParts.Add(string.Join(":", raw));
                if (raw.Length >= 3 && Sides.TryParse(raw[0], out var side) && Port.TryParseKind(raw[1], out var kind)
                    && Port.TryParseProfile(raw[2], out var profile) && bySide[(int)side] == null)
                {
                    var port = new Port(side, kind, profile);
                    bySide[(int)side] = port;
                    ports.Add(port);
                }
                else wellFormed = false;
            }
            Ports = ports;
            portBySide = wellFormed ? bySide : null;
            Signature = signatureOk ? JigsawCore.JoinSignature(signatureParts) : null;

            var sockets = new List<Side>();
            if (socketSides != null)
            {
                foreach (var s in socketSides) if (Sides.TryParse(s, out var side)) sockets.Add(side);
            }
            else
            {
                foreach (var p in ports) if (p.Kind == PortKind.Socket) sockets.Add(p.Side);
            }
            SocketSides = sockets;
        }

        /// <summary>Model id, e.g. <c>"m_we"</c>.</summary>
        public string Id { get; }

        /// <summary>Raw colour field from the data (<c>"none"</c> for every shipped model). Null when it was not a string.</summary>
        public string Color { get; }

        /// <summary>The well-formed ports, in data order.</summary>
        public IReadOnlyList<Port> Ports { get; }

        /// <summary>
        /// Sides that hold a socket, as listed in the data (<c>socketSides</c>). The UI uses it to shift the word away from the socket notches.
        /// </summary>
        public IReadOnlyList<Side> SocketSides { get; }

        /// <summary>SVG outline (<c>M x,y L x,y ... Z</c>) in a 100-unit cell, y down. Parse it with <see cref="PathParser"/>.</summary>
        public string Path { get; }

        /// <summary>
        /// The outline as polygons in cell space (0..100, y down; tabs reach about -21..121), parsed from <see cref="Path"/>
        /// on first use with <see cref="PathParser.ParseSubpaths"/>. Every shipped model has exactly one polygon.
        /// Empty when there is no path. Scale by <c>unit / 100</c> to draw with Painter2D.
        /// </summary>
        /// <exception cref="FormatException">The path uses unsupported commands (thrown on first access).</exception>
        public IReadOnlyList<IReadOnlyList<CellPoint>> Outline
            => outline ??= Path == null ? Array.Empty<IReadOnlyList<CellPoint>>() : PathParser.ParseSubpaths(Path);

        private IReadOnlyList<IReadOnlyList<CellPoint>> outline;

        /// <summary>
        /// True when the model can be placed: valid colour, a ports array, and every port well formed with no repeated side
        /// (core.js <c>validModel</c> and <c>portMap</c> both pass).
        /// </summary>
        public bool IsUsable => IsValidModel && portBySide != null;

        /// <summary>core.js <c>validModel</c>: colour is none/yellow/blue and ports is an array.</summary>
        internal bool IsValidModel { get; }

        /// <summary>core.js <c>portMap(model) !== null</c>.</summary>
        internal bool HasPortMap => portBySide != null;

        /// <summary>core.js <c>signature(model.ports)</c>; null when a raw port was not an array of strings.</summary>
        internal string Signature { get; }

        /// <summary>Port on <paramref name="side"/>. Always false when the ports are malformed.</summary>
        public bool TryGetPort(Side side, out Port port)
        {
            if (portBySide != null && portBySide[(int)side] is Port p) { port = p; return true; }
            port = default;
            return false;
        }

        /// <summary>Port on <paramref name="side"/>, or null.</summary>
        internal Port? PortOn(Side side) => portBySide?[(int)side];

        /// <summary>Reads one entry of the <c>models</c> table. Never throws on malformed content; such models are simply not usable.</summary>
        internal static JigsawModel FromJson(string id, JsonNode node)
        {
            var obj = node as JsonObject;
            if (obj == null) return new JigsawModel(id, null, false, null, null, null);
            string color = obj.Get("color")?.AsString;
            var portsNode = obj.Get("ports") as JsonArray;
            List<string[]> raw = null;
            if (portsNode != null)
            {
                raw = new List<string[]>();
                foreach (var p in portsNode.Items)
                {
                    if (p is JsonArray arr) raw.Add(arr.Items.Select(e => e.AsString).ToArray());
                    else raw.Add(null);
                }
            }
            List<string> socketSides = null;
            if (obj.Get("socketSides") is JsonArray ss) socketSides = ss.Items.Select(e => e.AsString).Where(s => s != null).ToList();
            return new JigsawModel(id, color, portsNode != null, raw, socketSides, obj.Get("path")?.AsString);
        }

        private static IReadOnlyList<string[]> ToRaw(IEnumerable<Port> ports)
        {
            if (ports == null) throw new ArgumentNullException(nameof(ports));
            return ports.Select(p => new[] { p.Side.Code(), Port.KindCode(p.Kind), Port.ProfileCode(p.Profile) }).ToList();
        }
    }

    /// <summary>
    /// The model table (models.json). Enumeration follows JavaScript property order
    /// (integer-like keys ascending first, then insertion order) so <see cref="JigsawCore.FindModel"/> picks the same model as core.js.
    /// </summary>
    public sealed class ModelLibrary
    {
        private readonly Dictionary<string, JigsawModel> byId;

        /// <summary>Creates a table from models (later duplicates of an id replace earlier ones in place).</summary>
        public ModelLibrary(IEnumerable<JigsawModel> models, IEnumerable<string> palette = null)
        {
            if (models == null) throw new ArgumentNullException(nameof(models));
            byId = new Dictionary<string, JigsawModel>(StringComparer.Ordinal);
            var insertion = new List<string>();
            foreach (var m in models)
            {
                if (!byId.ContainsKey(m.Id)) insertion.Add(m.Id);
                byId[m.Id] = m;
            }
            var integerKeys = insertion.Where(IsArrayIndex).OrderBy(k => uint.Parse(k, System.Globalization.CultureInfo.InvariantCulture));
            InOrder = integerKeys.Concat(insertion.Where(k => !IsArrayIndex(k))).Select(k => byId[k]).ToList();
            Palette = palette?.ToList() ?? new List<string>();
        }

        /// <summary>Models in JavaScript enumeration order.</summary>
        public IReadOnlyList<JigsawModel> InOrder { get; }

        /// <summary>Models by id.</summary>
        public IReadOnlyDictionary<string, JigsawModel> Models => byId;

        /// <summary>Palette model ids (the <c>palette</c> array of models.json; empty when absent).</summary>
        public IReadOnlyList<string> Palette { get; }

        /// <summary>Number of models.</summary>
        public int Count => byId.Count;

        /// <summary>Looks a model up by id.</summary>
        public bool TryGet(string id, out JigsawModel model)
        {
            if (id != null && byId.TryGetValue(id, out model)) return true;
            model = null;
            return false;
        }

        /// <summary>Model by id, or null.</summary>
        public JigsawModel Get(string id) => TryGet(id, out var m) ? m : null;

        /// <summary>Loads models.json text (either <c>{"models":{...},"palette":[...]}</c> or a bare models table).</summary>
        /// <exception cref="FormatException">The text is not valid JSON or the root is not an object.</exception>
        public static ModelLibrary Load(string modelsJsonText) => FromJson(MiniJson.ParseNode(modelsJsonText));

        /// <summary>Builds the table from a parsed JSON root, unwrapping <c>root.models</c> like core.js <c>unwrap</c>.</summary>
        /// <exception cref="FormatException">The root is not an object.</exception>
        public static ModelLibrary FromJson(JsonNode root)
        {
            var obj = root as JsonObject ?? throw new FormatException("models.json root must be an object.");
            JsonObject table = obj;
            var inner = obj.Get("models");
            if (inner != null && inner.IsTruthy) table = inner as JsonObject ?? new JsonObject();
            var models = table.Keys.Select(k => JigsawModel.FromJson(k, table.Get(k)));
            IEnumerable<string> palette = null;
            if (obj.Get("palette") is JsonArray pal) palette = pal.Items.Select(e => e.AsString).Where(s => s != null);
            return new ModelLibrary(models, palette);
        }

        /// <summary>ECMAScript array-index test (canonical uint32 below 2^32 - 1) used for property ordering.</summary>
        private static bool IsArrayIndex(string key)
        {
            if (key.Length == 0 || key.Length > 10) return false;
            if (key.Length > 1 && key[0] == '0') return false;
            foreach (char c in key) if (c < '0' || c > '9') return false;
            return ulong.Parse(key, System.Globalization.CultureInfo.InvariantCulture) < 4294967295UL;
        }
    }
}
