using System;
using System.Collections.Generic;
using System.Linq;

namespace OUAT.Jigsaw
{
    /// <summary>
    /// Port of the trial <c>core.js</c> (기록/초록테두리_무색모형_2026-10-20): joint checks, green-border checks, sentence reading,
    /// canonical form and automatic layout. Pure C#, deterministic, results identical to core.js (see tools/jigsaw-tests).
    /// </summary>
    public static class JigsawCore
    {
        /// <summary>core.js board width (columns).</summary>
        public const int DefaultBoardWidth = 7;
        /// <summary>core.js board height (rows).</summary>
        public const int DefaultBoardHeight = 6;
        /// <summary>Most pieces on one board.</summary>
        public const int MaxPieces = 12;
        /// <summary>Most outgoing joints from one piece.</summary>
        public const int MaxBranches = 3;
        /// <summary>Most yellow words in a row (a green border counts as one word).</summary>
        public const int MaxYellowRun = 3;
        /// <summary>Cell of the root piece in <see cref="Build"/>.</summary>
        public const int BuildRootX = 0, BuildRootY = 2;
        /// <summary>Search step budget of <see cref="Build"/>.</summary>
        public const int BuildBudget = 400000;

        // Messages copied verbatim from core.js.
        private const string MsgEmpty = "조각을 놓아 주세요.";
        private const string MsgPieceLimit = "조각은 열두 개까지 놓아 주세요.";
        private const string MsgInvalidPiece = "조각 정보를 확인해 주세요.";
        private const string MsgOutOfBounds = "조각을 판 안의 칸에 맞춰 주세요.";
        private const string MsgInvalidModel = "모형을 확인해 주세요.";
        private const string MsgEmptyWord = "빈 조각에 글자를 넣어 주세요.";
        private const string MsgRotation = "모형은 돌리지 않고 사용해 주세요.";
        private const string MsgOverlap = "겹친 조각을 옮겨 주세요.";
        private const string MsgPortMismatch = "맞닿은 홈과 돌출부를 확인해 주세요.";
        private const string MsgGroupOverlap = "한 조각은 테두리 하나에만 들어갈 수 있어요.";
        private const string MsgGroupSize = "초록 테두리는 2~3칸을 묶어요.";
        private const string MsgGroupMissing = "테두리 안 칸에 조각을 채워 주세요.";
        private const string MsgGroupBranchInner = "테두리 안은 갈래 없이 한 줄로 이어 주세요.";
        private const string MsgGroupJoint = "테두리 안 조각을 이음새(돌출→홈)를 따라 한 줄로 이어 주세요.";
        private const string MsgGroupBranchIn = "테두리 안으로는 첫 조각으로만 들어올 수 있어요.";
        private const string MsgGroupBranchOut = "테두리 밖으로는 끝 조각에서만 이어 나갈 수 있어요.";
        private const string MsgDisconnected = "떨어진 조각을 연결해 주세요.";
        private const string MsgCycle = "연결이 고리로 돌아오지 않게 해 주세요.";
        private const string MsgMultipleParents = "한 조각으로 들어오는 연결을 하나로 정리해 주세요.";
        private const string MsgRootCount = "한 표현으로 이어 주세요.";
        private const string MsgBranchLimit = "한 조각에서 세 갈래까지 이어 주세요.";
        private const string MsgChainLimit = "노란 조각은 연속 세 개까지 연결해 주세요.";
        private const string MsgBuildBranches = "한 조각에서 세 갈래까지 만들 수 있습니다.";
        private const string MsgBuildSize = "표현은 열두 조각까지 만들 수 있습니다.";
        private const string MsgBuildNoModel = "필요한 모형이 없습니다: ";

        private static readonly Side[] EastSouth = { Side.E, Side.S };

        // ───────────────────────────── colours, trees ─────────────────────────────

        /// <summary>core.js <c>colorOf</c>: <c>"blue"</c> or <c>"yellow"</c>. Null <paramref name="blueWords"/> uses <see cref="WordColors.DefaultBlueWords"/>.</summary>
        public static string ColorOf(string word, ISet<string> blueWords = null) => WordColors.ColorOf(word, blueWords).Code();

        /// <summary>
        /// core.js <c>canonical</c>. Accepts a <see cref="SpecNode"/>, an <see cref="AnalyzedNode"/>, or spec JSON
        /// (<see cref="MiniJson.Parse"/> output or a <see cref="JsonNode"/>).
        /// </summary>
        /// <exception cref="SpecFormatException">Not a spec.</exception>
        public static string Canonical(object tree) => ToSpec(tree).Canonical();

        /// <summary>core.js <c>eq</c>: same sentence regardless of child order. A malformed spec compares unequal instead of throwing.</summary>
        /// <param name="tree">A <see cref="SpecNode"/>, <see cref="AnalyzedNode"/> or spec JSON.</param>
        /// <param name="spec">A <see cref="SpecNode"/>, <see cref="AnalyzedNode"/> or spec JSON.</param>
        public static bool Eq(object tree, object spec)
        {
            try { return Canonical(tree) == Canonical(spec); }
            catch (SpecFormatException) { return false; }
        }

        private static SpecNode ToSpec(object tree) => tree is AnalyzedNode analyzed ? analyzed.ToSpecNode() : SpecNode.FromJson(tree);

        // ───────────────────────────── models ─────────────────────────────

        /// <summary>core.js <c>signature</c>: ports as <c>side:kind:profile</c>, sorted, joined with <c>|</c>.</summary>
        public static string Signature(IEnumerable<Port> ports)
            => JoinSignature((ports ?? throw new ArgumentNullException(nameof(ports))).Select(p => p.ToString()));

        internal static string JoinSignature(IEnumerable<string> parts)
        {
            var list = parts.ToList();
            list.Sort(StringComparer.Ordinal);
            return string.Join("|", list);
        }

        /// <summary>core.js <c>findModel</c>: first model (JS property order) with exactly these ports, or null.</summary>
        public static string FindModel(ModelLibrary models, IEnumerable<Port> ports)
        {
            if (models == null) return null;
            string sig = Signature(ports);
            foreach (var m in models.InOrder)
                if (m.IsValidModel && m.Signature == sig) return m.Id;
            return null;
        }

        private static JigsawModel UsableModel(ModelLibrary models, Piece p)
        {
            var m = models?.Get(p.ModelId);
            return m != null && m.IsValidModel && m.HasPortMap ? m : null;
        }

        private static void RequireNoNullPieces(IReadOnlyList<Piece> pieces)
        {
            if (pieces == null) throw new ArgumentNullException(nameof(pieces));
            for (int i = 0; i < pieces.Count; i++)
                if (pieces[i] == null) throw new ArgumentException($"pieces[{i}] is null.", nameof(pieces));
        }

        private static Dictionary<(int, int), Piece> CellMap(IReadOnlyList<Piece> pieces)
        {
            var cells = new Dictionary<(int, int), Piece>();
            foreach (var p in pieces) cells[(p.X, p.Y)] = p; // later piece wins, like Map.set
            return cells;
        }

        // ───────────────────────────── local edges ─────────────────────────────

        /// <summary>
        /// core.js <c>localEdges</c>: joints between touching pieces whose ports fit, ignoring every other board error.
        /// Used for green-border tools and cell picking.
        /// </summary>
        /// <exception cref="ArgumentException">A piece is null.</exception>
        public static IReadOnlyList<Joint> LocalEdges(IReadOnlyList<Piece> pieces, ModelLibrary models)
        {
            RequireNoNullPieces(pieces);
            var cells = CellMap(pieces);
            var edges = new List<Joint>();
            foreach (var p in pieces)
            {
                foreach (var side in EastSouth)
                {
                    if (!cells.TryGetValue((p.X + side.Dx(), p.Y + side.Dy()), out var q)) continue;
                    var pa = UsableModel(models, p);
                    var qb = UsableModel(models, q);
                    if (pa == null || qb == null) continue;
                    var a = pa.PortOn(side);
                    var b = qb.PortOn(side.Opposite());
                    if (a == null || b == null || !a.Value.Fits(b.Value)) continue;
                    edges.Add(a.Value.Kind == PortKind.Tab ? new Joint(p.Id, q.Id, a.Value.Profile) : new Joint(q.Id, p.Id, a.Value.Profile));
                }
            }
            return edges;
        }

        // ───────────────────────────── green border ─────────────────────────────

        /// <summary>
        /// core.js <c>checkGroup</c>: a green border is 2–3 pieces joined in one line without branches (straight or bent);
        /// outside joints may enter only the first piece and leave only from the last. Reading order follows the joints.
        /// </summary>
        /// <exception cref="ArgumentException">A piece is null.</exception>
        public static GroupCheckResult CheckGroup(IReadOnlyList<Piece> pieces, ModelLibrary models, IReadOnlyList<string> ids)
        {
            RequireNoNullPieces(pieces);
            GroupCheckResult Fail(string code, string message) => new GroupCheckResult(false, code, message, null);

            if (ids == null || ids.Count < 2 || ids.Count > 3 || ids.Distinct(StringComparer.Ordinal).Count() != ids.Count)
                return Fail(JigsawCodes.GroupSize, MsgGroupSize);

            var byId = new Dictionary<string, Piece>(StringComparer.Ordinal);
            foreach (var p in pieces) if (p.Id != null) byId[p.Id] = p;
            var gp = new List<Piece>();
            foreach (var id in ids)
            {
                if (id == null || !byId.TryGetValue(id, out var p)) return Fail(JigsawCodes.GroupMissing, MsgGroupMissing);
                gp.Add(p);
            }
            var cells = CellMap(pieces);
            var inside = new HashSet<string>(ids, StringComparer.Ordinal);
            bool Inside(Piece q) => q.Id != null && inside.Contains(q.Id);

            foreach (var p in gp) if (UsableModel(models, p) == null) return Fail(JigsawCodes.InvalidModel, MsgInvalidModel);

            var inner = new List<(string from, string to)>();
            foreach (var p in gp)
            {
                var mine = UsableModel(models, p);
                foreach (var side in Sides.All)
                {
                    if (!cells.TryGetValue((p.X + side.Dx(), p.Y + side.Dy()), out var q)) continue;
                    var a = mine.PortOn(side);
                    var b = UsableModel(models, q)?.PortOn(side.Opposite());
                    if (a == null && b == null) continue;
                    if (a == null || b == null || !a.Value.Fits(b.Value)) return Fail(JigsawCodes.PortMismatch, MsgPortMismatch);
                    if (Inside(q) && a.Value.Kind == PortKind.Tab) inner.Add((p.Id, q.Id));
                }
            }

            var outs = ids.ToDictionary(id => id, _ => new List<string>(), StringComparer.Ordinal);
            var ins = ids.ToDictionary(id => id, _ => new List<string>(), StringComparer.Ordinal);
            foreach (var (from, to) in inner) { outs[from].Add(to); ins[to].Add(from); }
            if (ids.Any(id => outs[id].Count > 1 || ins[id].Count > 1)) return Fail(JigsawCodes.GroupBranch, MsgGroupBranchInner);

            var starts = ids.Where(id => ins[id].Count == 0).ToList();
            if (inner.Count != ids.Count - 1 || starts.Count != 1) return Fail(JigsawCodes.GroupJoint, MsgGroupJoint);
            var order = new List<string> { starts[0] };
            while (outs[order[order.Count - 1]].Count > 0) order.Add(outs[order[order.Count - 1]][0]);
            if (order.Count != ids.Count) return Fail(JigsawCodes.GroupJoint, MsgGroupJoint);

            for (int i = 0; i < order.Count; i++)
            {
                var p = byId[order[i]];
                var mine = UsableModel(models, p);
                foreach (var side in Sides.All)
                {
                    if (!cells.TryGetValue((p.X + side.Dx(), p.Y + side.Dy()), out var q) || Inside(q)) continue;
                    var a = mine.PortOn(side);
                    var b = UsableModel(models, q)?.PortOn(side.Opposite());
                    if (a == null && b == null) continue;
                    // The fit check above guarantees a != null here.
                    bool incoming = a.Value.Kind == PortKind.Socket;
                    if (incoming && i != 0) return Fail(JigsawCodes.GroupBranch, MsgGroupBranchIn);
                    if (!incoming && i != order.Count - 1) return Fail(JigsawCodes.GroupBranch, MsgGroupBranchOut);
                }
            }
            return new GroupCheckResult(true, JigsawCodes.Group, null, order);
        }

        // ───────────────────────────── analyze ─────────────────────────────

        /// <summary>
        /// core.js <c>analyze</c>: validates a board and reads it as one sentence tree.
        /// Checks run in core.js order and stop at the first failure; see <see cref="JigsawCodes"/>.
        /// </summary>
        /// <param name="pieces">Board pieces. The first piece seeds the connectivity check (order matters only for which error wins).</param>
        /// <param name="models">Model table.</param>
        /// <param name="blueWords">Blue words; null uses <see cref="WordColors.DefaultBlueWords"/>.</param>
        /// <param name="options">Green borders, compound table and board size; null for none / 7×6.</param>
        public static AnalyzeResult Analyze(IReadOnlyList<Piece> pieces, ModelLibrary models, ISet<string> blueWords = null, AnalyzeOptions options = null)
        {
            var blues = blueWords ?? WordColors.DefaultBlueWords;
            var groups = options?.Groups ?? Array.Empty<IReadOnlyList<string>>();
            var lexicon = options?.Lexicon;
            int width = options?.BoardWidth ?? DefaultBoardWidth, height = options?.BoardHeight ?? DefaultBoardHeight;
            var edges = new List<Joint>();
            AnalyzeResult Fail(string code, string message, int? group = null)
                => new AnalyzeResult(false, code, message, null, null, edges.ToList(), null, group);

            if (pieces == null || pieces.Count == 0) return Fail(JigsawCodes.Empty, MsgEmpty);
            if (pieces.Count > MaxPieces) return Fail(JigsawCodes.PieceLimit, MsgPieceLimit);

            var ids = new Dictionary<string, Piece>(StringComparer.Ordinal);
            var cells = new Dictionary<(int, int), Piece>();
            var ports = new Dictionary<string, JigsawModel>(StringComparer.Ordinal);
            foreach (var p in pieces)
            {
                if (p == null || p.Id == null || ids.ContainsKey(p.Id)) return Fail(JigsawCodes.InvalidPiece, MsgInvalidPiece);
                if (p.X < 0 || p.X >= width || p.Y < 0 || p.Y >= height) return Fail(JigsawCodes.OutOfBounds, MsgOutOfBounds);
                var model = models?.Get(p.ModelId);
                if (model == null || !model.IsValidModel) return Fail(JigsawCodes.InvalidModel, MsgInvalidModel);
                if (p.Word == null || IsBlank(p.Word)) return Fail(JigsawCodes.EmptyWord, MsgEmptyWord);
                if (p.Rotation != 0 && p.Rotation % 360 != 0) return Fail(JigsawCodes.Rotation, MsgRotation);
                if (cells.ContainsKey((p.X, p.Y))) return Fail(JigsawCodes.Overlap, MsgOverlap);
                if (!model.HasPortMap) return Fail(JigsawCodes.InvalidModel, MsgInvalidModel);
                ids[p.Id] = p;
                cells[(p.X, p.Y)] = p;
                ports[p.Id] = model;
            }

            foreach (var p in pieces)
            {
                foreach (var side in EastSouth)
                {
                    if (!cells.TryGetValue((p.X + side.Dx(), p.Y + side.Dy()), out var q)) continue;
                    var a = ports[p.Id].PortOn(side);
                    var b = ports[q.Id].PortOn(side.Opposite());
                    if (a == null && b == null) continue;
                    if (a == null || b == null || !a.Value.Fits(b.Value)) return Fail(JigsawCodes.PortMismatch, MsgPortMismatch);
                    edges.Add(a.Value.Kind == PortKind.Tab ? new Joint(p.Id, q.Id, a.Value.Profile) : new Joint(q.Id, p.Id, a.Value.Profile));
                }
            }

            // Green borders (초록 테두리)
            var firstOf = new Dictionary<string, int>(StringComparer.Ordinal);
            var member = new Dictionary<string, int>(StringComparer.Ordinal);
            var ordered = new List<IReadOnlyList<string>>();
            for (int gi = 0; gi < groups.Count; gi++)
            {
                var g = groups[gi];
                if (g != null && g.Any(id => id != null && member.ContainsKey(id))) return Fail(JigsawCodes.GroupOverlap, MsgGroupOverlap, gi);
                var c = CheckGroup(pieces, models, g);
                if (!c.Ok) return Fail(c.Code, c.Message, gi);
                ordered.Add(c.OrderedIds);
                firstOf[c.OrderedIds[0]] = gi;
                foreach (var id in c.OrderedIds) member[id] = gi;
            }

            var incoming = pieces.ToDictionary(p => p.Id, _ => new List<string>(), StringComparer.Ordinal);
            var outgoing = pieces.ToDictionary(p => p.Id, _ => new List<string>(), StringComparer.Ordinal);
            foreach (var e in edges) { incoming[e.To].Add(e.From); outgoing[e.From].Add(e.To); }

            var reached = new HashSet<string>(StringComparer.Ordinal) { pieces[0].Id };
            var stack = new Stack<string>();
            stack.Push(pieces[0].Id);
            while (stack.Count > 0)
            {
                var id = stack.Pop();
                foreach (var next in incoming[id].Concat(outgoing[id]))
                    if (reached.Add(next)) stack.Push(next);
            }
            if (reached.Count != pieces.Count) return Fail(JigsawCodes.Disconnected, MsgDisconnected);

            var marks = new Dictionary<string, int>(StringComparer.Ordinal);
            bool Cyclic(string id)
            {
                marks.TryGetValue(id, out int mark);
                if (mark == 1) return true;
                if (mark == 2) return false;
                marks[id] = 1;
                foreach (var next in outgoing[id]) if (Cyclic(next)) return true;
                marks[id] = 2;
                return false;
            }
            if (pieces.Any(p => Cyclic(p.Id))) return Fail(JigsawCodes.Cycle, MsgCycle);
            if (pieces.Any(p => incoming[p.Id].Count > 1)) return Fail(JigsawCodes.MultipleParents, MsgMultipleParents);
            var roots = pieces.Where(p => incoming[p.Id].Count == 0).ToList();
            if (roots.Count != 1) return Fail(JigsawCodes.RootCount, MsgRootCount);
            if (pieces.Any(p => outgoing[p.Id].Count > MaxBranches)) return Fail(JigsawCodes.BranchLimit, MsgBranchLimit);

            bool tooLong = false;
            // A green border reads as one word: colour of its last piece, entered through the first piece, left from the last.
            AnalyzedNode Walk(string id, int previousYellow)
            {
                if (firstOf.TryGetValue(id, out int gi))
                {
                    var gids = ordered[gi];
                    var parts = gids.Select(x => ids[x].Word).ToList();
                    string key = string.Join("+", parts);
                    LexiconEntry entry = null;
                    bool known = lexicon != null && lexicon.TryGetValue(key, out entry) && entry != null;
                    string last = gids[gids.Count - 1];
                    var gcolor = WordColors.ColorOf(parts[parts.Count - 1], blues);
                    int gn = gcolor == WordColor.Yellow ? previousYellow + 1 : 0;
                    if (gn > MaxYellowRun) tooLong = true;
                    var gchildren = outgoing[last].Select(child => Walk(child, gn)).ToList();
                    return new AnalyzedNode(known ? entry.Word : "[" + string.Join(" ", parts) + "]", gcolor, gchildren,
                        null, gi, parts, gids, known);
                }
                var p = ids[id];
                var color = WordColors.ColorOf(p.Word, blues);
                int n = color == WordColor.Yellow ? previousYellow + 1 : 0;
                if (n > MaxYellowRun) tooLong = true;
                var children = outgoing[id].Select(child => Walk(child, n)).ToList();
                return new AnalyzedNode(p.Word, color, children, p.Id, null, null, null, false);
            }
            var tree = Walk(roots[0].Id, 0);
            if (tooLong) return Fail(JigsawCodes.ChainLimit, MsgChainLimit);
            return new AnalyzeResult(true, JigsawCodes.Parsed, "", tree, tree.ToSpecNode().Canonical(), edges.ToList(), ordered, null);
        }

        /// <summary>JavaScript <c>!s.trim()</c>: true when the string is empty or only ECMAScript whitespace / line terminators.</summary>
        internal static bool IsBlank(string s)
        {
            foreach (char c in s) if (!IsJsWhitespace(c)) return false;
            return true;
        }

        private static bool IsJsWhitespace(char c)
        {
            // ECMAScript WhiteSpace + LineTerminator (what String.prototype.trim removes). Differs from char.IsWhiteSpace:
            // U+FEFF counts, U+0085 and U+180E do not.
            int code = c;
            switch (code)
            {
                case 0x09: case 0x0A: case 0x0B: case 0x0C: case 0x0D: case 0x20:
                case 0xA0: case 0x1680: case 0x2028: case 0x2029: case 0x202F: case 0x205F: case 0x3000: case 0xFEFF:
                    return true;
                default:
                    return code >= 0x2000 && code <= 0x200A;
            }
        }

        // ───────────────────────────── build ─────────────────────────────

        private sealed class BuildNode
        {
            public string Word;
            public BuildNode Parent;
            public readonly List<BuildNode> Children = new List<BuildNode>();
            public int Index;
            public int Size;
        }

        /// <summary>
        /// core.js <c>build</c>: lays a spec out as pieces on the 7×6 board (root at (0,2); children tried right, down, left, up;
        /// bigger subtrees first), with round joints and the first matching model. Used to show creature sentences pre-assembled.
        /// Piece ids are <c>p0</c>, <c>p1</c>, … in spec pre-order.
        /// </summary>
        /// <exception cref="JigsawBuildException">More than 3 children, more than 12 words, no layout, a missing model, or the
        /// result does not analyze (e.g. <c>chain_limit</c> with the given blue words). Message is the core.js message.</exception>
        public static List<Piece> Build(SpecNode spec, ModelLibrary models, ISet<string> blueWords = null)
        {
            if (spec == null) throw new ArgumentNullException(nameof(spec));
            var blues = blueWords ?? WordColors.DefaultBlueWords;
            var nodes = new List<BuildNode>();

            BuildNode Flatten(SpecNode t, BuildNode parent)
            {
                var n = new BuildNode { Word = t.Word, Parent = parent, Index = nodes.Count };
                nodes.Add(n);
                if (t.Children.Count > MaxBranches) throw new JigsawBuildException(MsgBuildBranches);
                foreach (var child in t.Children) n.Children.Add(Flatten(child, n));
                n.Size = 1 + n.Children.Sum(c => c.Size);
                return n;
            }
            var root = Flatten(spec, null);
            if (nodes.Count > MaxPieces) throw new JigsawBuildException(MsgBuildSize);

            var traversal = new List<BuildNode>();
            void Order(BuildNode n)
            {
                traversal.Add(n);
                foreach (var c in n.Children.OrderByDescending(c => c.Size)) Order(c); // stable, like Array.prototype.sort
            }
            Order(root);

            const int width = DefaultBoardWidth, height = DefaultBoardHeight;
            var used = new HashSet<(int, int)>();
            var positions = new Dictionary<int, (int x, int y)>();
            int budget = BuildBudget;
            bool InBounds(int x, int y) => x >= 0 && x < width && y >= 0 && y < height;
            int Rank((int x, int y) a, (int x, int y) p) => a.x > p.x ? 0 : a.y > p.y ? 1 : a.x < p.x ? 2 : 3;

            bool Search(int i)
            {
                if (i == traversal.Count) return true;
                if (--budget < 0) return false;
                var n = traversal[i];
                List<(int x, int y)> choices;
                if (n.Parent != null)
                {
                    var pp = positions[n.Parent.Index];
                    choices = Sides.All.Select(s => (pp.x + s.Dx(), pp.y + s.Dy())).ToList();
                    choices = choices.OrderBy(c => Rank(c, pp)).ToList();
                }
                else choices = new List<(int x, int y)> { (BuildRootX, BuildRootY) };
                foreach (var pos in choices)
                {
                    if (!InBounds(pos.x, pos.y) || used.Contains(pos)) continue;
                    int free = Sides.All.Count(s => InBounds(pos.x + s.Dx(), pos.y + s.Dy()) && !used.Contains((pos.x + s.Dx(), pos.y + s.Dy())));
                    if (free < n.Children.Count) continue;
                    positions[n.Index] = pos;
                    used.Add(pos);
                    if (Search(i + 1)) return true;
                    used.Remove(pos);
                    positions.Remove(n.Index);
                }
                return false;
            }
            if (!Search(0)) throw new JigsawBuildException($"이 표현을 {width}×{height} 판에 배치할 수 없습니다.");

            Side SideBetween(BuildNode from, BuildNode to)
            {
                var a = positions[from.Index];
                var b = positions[to.Index];
                return Sides.All.First(s => a.x + s.Dx() == b.x && a.y + s.Dy() == b.y);
            }

            var pieces = new List<Piece>();
            foreach (var n in nodes)
            {
                var portList = new List<Port>();
                if (n.Parent != null) portList.Add(new Port(SideBetween(n, n.Parent), PortKind.Socket, PortProfile.Round));
                foreach (var c in n.Children) portList.Add(new Port(SideBetween(n, c), PortKind.Tab, PortProfile.Round));
                var model = FindModel(models, portList);
                if (model == null) throw new JigsawBuildException(MsgBuildNoModel + Signature(portList));
                var pos = positions[n.Index];
                pieces.Add(new Piece("p" + n.Index, model, n.Word, pos.x, pos.y));
            }
            var check = Analyze(pieces, models, blues);
            if (!check.Ok) throw new JigsawBuildException(check.Message);
            return pieces;
        }

        /// <summary>Non-throwing <see cref="Build"/>; <paramref name="error"/> holds the core.js message.</summary>
        public static bool TryBuild(SpecNode spec, ModelLibrary models, ISet<string> blueWords, out List<Piece> pieces, out string error)
        {
            try
            {
                pieces = Build(spec, models, blueWords);
                error = null;
                return true;
            }
            catch (JigsawBuildException e)
            {
                pieces = null;
                error = e.Message;
                return false;
            }
        }
    }
}
