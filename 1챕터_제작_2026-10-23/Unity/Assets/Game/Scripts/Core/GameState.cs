using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;

namespace OUAT.Core
{
    /// <summary>글자 하나에 대해 플레이어가 아는 것: 본 적 있음, 추측(직접 쓴 한 줄), 메모, 써서 통함, 확정.</summary>
    [Serializable]
    public class WordState
    {
        public string id;
        public bool seen;
        public string guess = "";
        public string memo = "";
        public bool usedOk;          // 대화·장치에서 써서 통한 적 있음
        public bool confirmed;
        public string seenAt = "";   // 처음 본 곳(장소 id)
        public bool readConfirmed;   // 새겨진 문장을 다 맞게 읽어 확정됨
    }

    [Serializable]
    class SaveData
    {
        public int version = 1;
        public List<string> flags = new List<string>();
        public List<WordState> words = new List<WordState>();
        public List<string> readInscriptions = new List<string>();
        public float px, py, pz;
        public bool hasPos;
        public string savedAt;
    }

    /// <summary>게임 진행 상태의 단일 원본. 깃발(flag)·글자 상태·읽어 낸 새김. 바뀌면 Changed가 울린다.</summary>
    public class GameState
    {
        readonly HashSet<string> flags = new HashSet<string>();
        readonly Dictionary<string, WordState> words = new Dictionary<string, WordState>();
        readonly HashSet<string> readInscriptions = new HashSet<string>();

        public event Action Changed;
        public event Action<string> FlagSet;
        public event Action<string> WordConfirmed;
        public event Action<string> WordSeen;

        public Vector3? SavedPlayerPosition { get; private set; }

        public bool Has(string flag) => !string.IsNullOrEmpty(flag) && flags.Contains(flag);
        public IEnumerable<string> Flags => flags;

        public void Set(string flag)
        {
            if (string.IsNullOrEmpty(flag) || !flags.Add(flag)) return;
            FlagSet?.Invoke(flag);
            Changed?.Invoke();
        }

        public void Unset(string flag)
        {
            if (flags.Remove(flag)) Changed?.Invoke();
        }

        public WordState Word(string id)
        {
            if (!words.TryGetValue(id, out var w)) { w = new WordState { id = id }; words[id] = w; }
            return w;
        }

        public IEnumerable<WordState> SeenWords => words.Values.Where(w => w.seen);

        public void See(string wordId, string place)
        {
            var w = Word(wordId);
            if (w.seen) return;
            w.seen = true; w.seenAt = place ?? "";
            WordSeen?.Invoke(wordId);
            Changed?.Invoke();
        }

        public void SetGuess(string wordId, string guess, Func<string, string, bool> isCorrect)
        {
            var w = Word(wordId);
            w.guess = (guess ?? "").Trim();
            TryConfirm(w, isCorrect);
            Changed?.Invoke();
        }

        public void SetMemo(string wordId, string memo) { Word(wordId).memo = memo ?? ""; Changed?.Invoke(); }

        /// <summary>대화·장치에서 이 글자를 써서 통했다. 추측이 맞으면 확정.</summary>
        public void MarkUsed(string wordId, Func<string, string, bool> isCorrect)
        {
            var w = Word(wordId);
            w.usedOk = true;
            TryConfirm(w, isCorrect);
            Changed?.Invoke();
        }

        /// <summary>새겨진 문장을 통째로 맞게 읽음 — 문장 속 글자를 근거 없이도 함께 확정(뜻-24).</summary>
        public void ConfirmByReading(IEnumerable<string> wordIds, string inscriptionId)
        {
            foreach (var id in wordIds)
            {
                var w = Word(id);
                if (w.confirmed) continue;
                w.confirmed = true; w.readConfirmed = true;
                WordConfirmed?.Invoke(id);
            }
            if (!string.IsNullOrEmpty(inscriptionId)) readInscriptions.Add(inscriptionId);
            Changed?.Invoke();
        }

        public bool InscriptionRead(string id) => readInscriptions.Contains(id);

        void TryConfirm(WordState w, Func<string, string, bool> isCorrect)
        {
            if (w.confirmed || !w.usedOk || string.IsNullOrEmpty(w.guess) || isCorrect == null) return;
            if (!isCorrect(w.id, w.guess)) return;
            w.confirmed = true;
            WordConfirmed?.Invoke(w.id);
        }

        // ── 저장 ─────────────────────────────────────────
        public static string SavePath => Path.Combine(Application.persistentDataPath, "chapter1_save.json");

        public void Save(Vector3? playerPos)
        {
            var d = new SaveData
            {
                flags = flags.ToList(),
                words = words.Values.ToList(),
                readInscriptions = readInscriptions.ToList(),
                savedAt = DateTime.Now.ToString("s")
            };
            if (playerPos.HasValue) { d.hasPos = true; d.px = playerPos.Value.x; d.py = playerPos.Value.y; d.pz = playerPos.Value.z; }
            try { File.WriteAllText(SavePath, JsonUtility.ToJson(d, true)); }
            catch (Exception e) { Debug.LogWarning("[OUAT] 저장 실패: " + e.Message); }
        }

        public static bool HasSave => File.Exists(SavePath);

        public bool Load()
        {
            if (!HasSave) return false;
            try
            {
                var d = JsonUtility.FromJson<SaveData>(File.ReadAllText(SavePath));
                flags.Clear(); words.Clear(); readInscriptions.Clear();
                foreach (var f in d.flags) flags.Add(f);
                foreach (var w in d.words) words[w.id] = w;
                foreach (var r in d.readInscriptions) readInscriptions.Add(r);
                SavedPlayerPosition = d.hasPos ? new Vector3(d.px, d.py, d.pz) : (Vector3?)null;
                Changed?.Invoke();
                return true;
            }
            catch (Exception e) { Debug.LogWarning("[OUAT] 불러오기 실패: " + e.Message); return false; }
        }

        public static void DeleteSave() { if (HasSave) File.Delete(SavePath); }
    }
}
