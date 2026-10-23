using System.Linq;
using UnityEditor;
using UnityEngine;

namespace OUAT.EditorTools
{
    /// <summary>
    /// 블렌더 캐릭터 FBX(뼈대 + 클립)를 Legacy Animation으로 가져온다 — 코드(ProceduralRig)가 클립 이름으로 바로 CrossFade.
    /// 반복 클립은 Loop, 한 번 하는 클립은 ClampForever(마지막 자세 유지). 루트 모션 없음.
    /// </summary>
    public class CharacterImport : AssetPostprocessor
    {
        public static readonly string[] Characters = { "Hero_Bluebird", "Kinopio", "Chief", "Villager", "Mother", "Silhouette", "Collector", "Fish" };
        static readonly string[] Loops = { "Idle", "Walk", "Run", "Talk", "BowHold", "LookUp", "Gather", "SitIdle", "FallTumble", "LieDown", "Kneel", "StandSway", "Hidden", "Carry", "Crowd", "RunAway", "Sulk", "Proclaim" };

        bool IsCharacter => IsAnimated(assetPath);
        public static bool IsAnimated(string path) => path.StartsWith("Assets/Game/Art/Models/") && Characters.Any(c => System.IO.Path.GetFileNameWithoutExtension(path).StartsWith(c)) && !System.IO.Path.GetFileNameWithoutExtension(path).StartsWith("FishProp");

        void OnPreprocessModel()
        {
            if (!IsCharacter) return;
            var mi = (ModelImporter)assetImporter;
            mi.animationType = ModelImporterAnimationType.Legacy;
            mi.importAnimation = true;
            mi.generateAnimations = ModelImporterGenerateAnimations.GenerateAnimations;
        }

        void OnPreprocessAnimation()
        {
            if (!IsCharacter) return;
            var mi = (ModelImporter)assetImporter;
            var clips = mi.defaultClipAnimations;
            if (clips == null || clips.Length == 0) return;
            foreach (var c in clips)
            {
                // 블렌더 테이크 이름이 "Armature|Walk"처럼 오면 뒤만
                var n = c.name.Contains("|") ? c.name.Substring(c.name.LastIndexOf('|') + 1) : c.name;
                c.name = n;
                c.loopTime = Loops.Contains(n);
                c.wrapMode = c.loopTime ? WrapMode.Loop : WrapMode.ClampForever;
            }
            mi.clipAnimations = clips;
        }
    }
}
