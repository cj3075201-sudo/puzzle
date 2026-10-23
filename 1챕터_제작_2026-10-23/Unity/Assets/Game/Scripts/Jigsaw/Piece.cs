using System;
using System.Collections.Generic;

namespace OUAT.Jigsaw
{
    /// <summary>A piece on the board: a model with a word (or empty) in a cell. Immutable.</summary>
    public sealed class Piece
    {
        /// <summary>Creates a piece.</summary>
        /// <param name="id">Unique id on the board. Null makes the board invalid (<c>invalid_piece</c>).</param>
        /// <param name="modelId">Model id in the <see cref="ModelLibrary"/>.</param>
        /// <param name="word">Word, or null / empty for an empty model.</param>
        /// <param name="x">Column, 0 at the left.</param>
        /// <param name="y">Row, 0 at the top.</param>
        /// <param name="rotation">Degrees. Only multiples of 360 are accepted by the analyzer (no rotation in this game).</param>
        public Piece(string id, string modelId, string word, int x, int y, int rotation = 0)
        {
            Id = id;
            ModelId = modelId;
            Word = word;
            X = x;
            Y = y;
            Rotation = rotation;
        }

        /// <summary>Unique id on the board.</summary>
        public string Id { get; }
        /// <summary>Model id.</summary>
        public string ModelId { get; }
        /// <summary>Word, or null / empty for an empty model.</summary>
        public string Word { get; }
        /// <summary>Column, 0 at the left.</summary>
        public int X { get; }
        /// <summary>Row, 0 at the top.</summary>
        public int Y { get; }
        /// <summary>Rotation in degrees (0 in practice).</summary>
        public int Rotation { get; }

        /// <summary>Copy with another word.</summary>
        public Piece WithWord(string word) => new Piece(Id, ModelId, word, X, Y, Rotation);
        /// <summary>Copy in another cell.</summary>
        public Piece WithCell(int x, int y) => new Piece(Id, ModelId, Word, x, y, Rotation);
        /// <summary>Copy with another model.</summary>
        public Piece WithModel(string modelId) => new Piece(Id, modelId, Word, X, Y, Rotation);

        /// <inheritdoc/>
        public override string ToString() => $"{Id}:{ModelId}:{Word}@{X},{Y}";
    }

    /// <summary>A joint between two touching pieces, directed from the tab piece to the socket piece (reading direction).</summary>
    public sealed class Joint : IEquatable<Joint>
    {
        /// <summary>Creates a joint.</summary>
        public Joint(string from, string to, PortProfile profile)
        {
            From = from;
            To = to;
            Profile = profile;
        }

        /// <summary>Id of the piece whose tab sticks out (read first).</summary>
        public string From { get; }
        /// <summary>Id of the piece whose socket receives the tab.</summary>
        public string To { get; }
        /// <summary>Joint profile.</summary>
        public PortProfile Profile { get; }

        /// <inheritdoc/>
        public bool Equals(Joint other) => other != null && From == other.From && To == other.To && Profile == other.Profile;
        /// <inheritdoc/>
        public override bool Equals(object obj) => Equals(obj as Joint);
        /// <inheritdoc/>
        public override int GetHashCode() => ((From?.GetHashCode() ?? 0) * 397) ^ (To?.GetHashCode() ?? 0) ^ (int)Profile;
        /// <inheritdoc/>
        public override string ToString() => $"{From}->{To}";
    }

    /// <summary>Error and success codes, identical to the <c>code</c> strings of core.js.</summary>
    public static class JigsawCodes
    {
        /// <summary>Success of <see cref="JigsawCore.Analyze"/>.</summary>
        public const string Parsed = "parsed";
        /// <summary>Success of <see cref="JigsawCore.CheckGroup"/>.</summary>
        public const string Group = "group";

        /// <summary>No pieces.</summary>
        public const string Empty = "empty";
        /// <summary>More than 12 pieces.</summary>
        public const string PieceLimit = "piece_limit";
        /// <summary>Null piece, null id or duplicate id.</summary>
        public const string InvalidPiece = "invalid_piece";
        /// <summary>Cell outside the board.</summary>
        public const string OutOfBounds = "out_of_bounds";
        /// <summary>Unknown or malformed model.</summary>
        public const string InvalidModel = "invalid_model";
        /// <summary>Empty (or whitespace-only) word.</summary>
        public const string EmptyWord = "empty_word";
        /// <summary>Rotated piece.</summary>
        public const string Rotation = "rotation";
        /// <summary>Two pieces in one cell.</summary>
        public const string Overlap = "overlap";
        /// <summary>Touching ports that do not fit (tab-tab, socket-socket, profile mismatch, port against a flat side).</summary>
        public const string PortMismatch = "port_mismatch";
        /// <summary>A piece in two green borders.</summary>
        public const string GroupOverlap = "group_overlap";
        /// <summary>Green border not 2–3 distinct pieces.</summary>
        public const string GroupSize = "group_size";
        /// <summary>Green border id without a piece.</summary>
        public const string GroupMissing = "group_missing";
        /// <summary>Branch inside a green border, or an outside joint on a middle piece.</summary>
        public const string GroupBranch = "group_branch";
        /// <summary>Green border pieces not one joined line.</summary>
        public const string GroupJoint = "group_joint";
        /// <summary>Pieces not all connected.</summary>
        public const string Disconnected = "disconnected";
        /// <summary>Joints form a loop.</summary>
        public const string Cycle = "cycle";
        /// <summary>A piece with two incoming joints.</summary>
        public const string MultipleParents = "multiple_parents";
        /// <summary>Not exactly one start piece. Unreachable once the earlier checks pass (kept for parity).</summary>
        public const string RootCount = "root_count";
        /// <summary>A piece with more than three outgoing joints.</summary>
        public const string BranchLimit = "branch_limit";
        /// <summary>More than three yellow words in a row.</summary>
        public const string ChainLimit = "chain_limit";
    }
}
