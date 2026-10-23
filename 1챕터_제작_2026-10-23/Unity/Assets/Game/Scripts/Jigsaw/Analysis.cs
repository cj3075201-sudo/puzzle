using System;
using System.Collections.Generic;
using System.Linq;

namespace OUAT.Jigsaw
{
    /// <summary>A known compound for a green border (합성 표 entry), e.g. <c>"물+가져가다+물건"</c> → 물통.</summary>
    public sealed class LexiconEntry
    {
        /// <summary>Creates an entry.</summary>
        public LexiconEntry(string word, WordColor? color = null)
        {
            Word = word ?? throw new ArgumentNullException(nameof(word));
            Color = color;
        }

        /// <summary>The compound's word.</summary>
        public string Word { get; }

        /// <summary>
        /// Colour recorded in the data. The analyzer does not use it: like core.js, a group's colour is the colour of its last part.
        /// </summary>
        public WordColor? Color { get; }
    }

    /// <summary>Optional inputs of <see cref="JigsawCore.Analyze"/>.</summary>
    public sealed class AnalyzeOptions
    {
        /// <summary>Green borders (초록 테두리): each 2–3 piece ids. Chapter 1 has none. A null entry is rejected as <c>group_size</c>.</summary>
        public IReadOnlyList<IReadOnlyList<string>> Groups { get; set; }

        /// <summary>Known compounds keyed by parts joined with <c>"+"</c> in reading order.</summary>
        public IReadOnlyDictionary<string, LexiconEntry> Lexicon { get; set; }

        /// <summary>Board columns for <c>out_of_bounds</c>. Default 7 (core.js).</summary>
        public int BoardWidth { get; set; } = JigsawCore.DefaultBoardWidth;

        /// <summary>Board rows for <c>out_of_bounds</c>. Default 6 (core.js).</summary>
        public int BoardHeight { get; set; } = JigsawCore.DefaultBoardHeight;
    }

    /// <summary>One word of an analyzed sentence. A green border reads as a single node.</summary>
    public sealed class AnalyzedNode
    {
        internal AnalyzedNode(string word, WordColor color, IReadOnlyList<AnalyzedNode> children, string pieceId,
            int? groupIndex, IReadOnlyList<string> parts, IReadOnlyList<string> groupPieceIds, bool known)
        {
            Word = word;
            Color = color;
            Children = children;
            PieceId = pieceId;
            GroupIndex = groupIndex;
            Parts = parts;
            GroupPieceIds = groupPieceIds;
            Known = known;
        }

        /// <summary>The word. For an unknown green border: <c>"[물건 가져가다 물]"</c>.</summary>
        public string Word { get; }

        /// <summary>Colour of the word (for a group: colour of its last part).</summary>
        public WordColor Color { get; }

        /// <summary>Words this one connects to, in joint order.</summary>
        public IReadOnlyList<AnalyzedNode> Children { get; }

        /// <summary>Piece id of a plain node; null for a green-border node (see <see cref="GroupPieceIds"/>).</summary>
        public string PieceId { get; }

        /// <summary>Index into <see cref="AnalyzeOptions.Groups"/> for a green-border node, otherwise null.</summary>
        public int? GroupIndex { get; }

        /// <summary>True for a green-border node.</summary>
        public bool IsGroup => GroupIndex.HasValue;

        /// <summary>Words inside the border in reading order (group nodes only).</summary>
        public IReadOnlyList<string> Parts { get; }

        /// <summary>Piece ids inside the border in reading order (group nodes only).</summary>
        public IReadOnlyList<string> GroupPieceIds { get; }

        /// <summary>True when the group is a known compound (group nodes only).</summary>
        public bool Known { get; }

        /// <summary>The plain word/children tree (what <see cref="SpecNode.Canonical"/> compares).</summary>
        public SpecNode ToSpecNode() => new SpecNode(Word, Children.Select(c => c.ToSpecNode()));
    }

    /// <summary>Result of <see cref="JigsawCore.Analyze"/>, mirroring the core.js result object.</summary>
    public sealed class AnalyzeResult
    {
        internal AnalyzeResult(bool ok, string code, string message, AnalyzedNode tree, string canonical,
            IReadOnlyList<Joint> joints, IReadOnlyList<IReadOnlyList<string>> groups, int? failedGroup)
        {
            Ok = ok;
            Code = code;
            Message = message;
            AnalyzedTree = tree;
            Tree = tree?.ToSpecNode();
            Canonical = canonical;
            Joints = joints;
            Groups = groups;
            FailedGroup = failedGroup;
        }

        /// <summary>True when the board reads as one sentence.</summary>
        public bool Ok { get; }

        /// <summary><see cref="JigsawCodes.Parsed"/> on success, otherwise an error code from <see cref="JigsawCodes"/>.</summary>
        public string Code { get; }

        /// <summary>Player-facing Korean message (empty on success), identical to core.js.</summary>
        public string Message { get; }

        /// <summary>The sentence as a plain word tree on success (compare with <see cref="JigsawCore.Eq"/>), otherwise null.</summary>
        public SpecNode Tree { get; }

        /// <summary>
        /// The same tree with reading details on success (word colours, piece ids, green-border parts and compound status),
        /// otherwise null. This is the object core.js returns as <c>tree</c>.
        /// </summary>
        public AnalyzedNode AnalyzedTree { get; }

        /// <summary>Canonical string of <see cref="Tree"/> on success, otherwise null.</summary>
        public string Canonical { get; }

        /// <summary>Joints found so far (all joints on success; on failure, those collected before the failing check, as in core.js).</summary>
        public IReadOnlyList<Joint> Joints { get; }

        /// <summary>Green borders in reading order (success only, otherwise null).</summary>
        public IReadOnlyList<IReadOnlyList<string>> Groups { get; }

        /// <summary>Index of the green border that failed (group errors only), otherwise null.</summary>
        public int? FailedGroup { get; }
    }

    /// <summary>Result of <see cref="JigsawCore.CheckGroup"/>.</summary>
    public sealed class GroupCheckResult
    {
        internal GroupCheckResult(bool ok, string code, string message, IReadOnlyList<string> orderedIds)
        {
            Ok = ok;
            Code = code;
            Message = message;
            OrderedIds = orderedIds;
        }

        /// <summary>True when the border is valid.</summary>
        public bool Ok { get; }
        /// <summary><see cref="JigsawCodes.Group"/> on success, otherwise the error code.</summary>
        public string Code { get; }
        /// <summary>Korean message (null on success, as core.js returns no message).</summary>
        public string Message { get; }
        /// <summary>Ids in reading order (joint direction) on success, otherwise null.</summary>
        public IReadOnlyList<string> OrderedIds { get; }
    }

    /// <summary>Thrown by <see cref="JigsawCore.Build"/> when a spec cannot be laid out. Message is the core.js message.</summary>
    public sealed class JigsawBuildException : Exception
    {
        /// <summary>Creates the exception.</summary>
        public JigsawBuildException(string message) : base(message) { }
    }
}
