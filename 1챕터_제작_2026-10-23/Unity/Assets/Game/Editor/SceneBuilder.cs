// 1챕터 장면을 데이터(chapter1.json)와 모델(Art/Models/*.fbx)로 조립한다. 다시 돌리면 장면을 새로 만든다.
// 배치 실행: tools/unity.ps1 -Method OUAT.EditorTools.SceneBuilder.Build
using System.Collections.Generic;
using System.IO;
using System.Linq;
using OUAT.Core;
using OUAT.UI;
using OUAT.World;
using Unity.AI.Navigation;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.AI;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.TextCore.Text;
using UnityEngine.UIElements;

namespace OUAT.EditorTools
{
    public static class SceneBuilder
    {
        const string ScenePath = "Assets/Game/Scenes/Chapter1.unity";
        const string MatDir = "Assets/Game/Art/Materials";
        const string ModelDir = "Assets/Game/Art/Models";
        static float MesaHeight = 1.5f;
        /// <summary>지형 담당의 구역 배치(art/layout_slice*.json) — 높이·사다리·빗장·잡동사니·빛 같은 값. 없으면 옛 값.</summary>
        static Dictionary<string, object> slice = new Dictionary<string, object>();
        static void LoadSlice()
        {
            slice = new Dictionary<string, object>();
            var dir = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "art"));
            foreach (var f in Directory.GetFiles(dir, "layout_slice*.json").OrderBy(x => x))
                if (Jigsaw.MiniJson.Parse(File.ReadAllText(f)) is Dictionary<string, object> d)
                    foreach (var kv in d) if (!slice.ContainsKey(kv.Key) || kv.Key == "fall_junk") slice[kv.Key] = kv.Value;
            MesaHeight = slice.TryGetValue("hilltop_height", out var h) ? J.F(h) : 1.5f;
        }
        static Vector3 SliceV3(string key, Vector3 fallback)
        {
            var l = slice.TryGetValue(key, out var o) ? o as List<object> : null;
            return l != null && l.Count >= 3 ? new Vector3(J.F(l[0]), J.F(l[1]), J.F(l[2])) : fallback;
        }
        static readonly Dictionary<string, Material> mats = new Dictionary<string, Material>();
        static Shader toon, ground, unlit;
        static Transform envRoot, propsRoot, npcRoot, zoneRoot;
        static ChapterData data;
        static readonly Dictionary<string, GameObject> propObjects = new Dictionary<string, GameObject>();
        static readonly List<Transform> alleyChairs = new List<Transform>();              // 골목 의자(등받이 새김 copies 자리)
        static readonly Dictionary<string, GameObject> boardForIns = new Dictionary<string, GameObject>();   // 그림판 자리 → 그 새김
        static System.Random rnd;

        static readonly Dictionary<string, (Vector2 c, float r)> PlacesFallback = new Dictionary<string, (Vector2, float)>
        {
            { "fall",  (new Vector2(-55, 30), 12) }, { "gate",  (new Vector2(-30, 18), 9) },
            { "plaza", (new Vector2(0, 10), 16) },   { "alley", (new Vector2(22, 26), 10) },
            { "field", (new Vector2(40, 0), 16) },   { "pond",  (new Vector2(58, -18), 8) },
        };
        static Dictionary<string, (Vector2 c, float r)> Places = new Dictionary<string, (Vector2, float)>();

        [MenuItem("OUAT/Build Chapter 1 Scene")]
        public static void Build()
        {
            ProjectSetup.Run();
            FixModelImport();
            EnsureFonts();
            EnsureTuning();
            EnsureTextureImport();
            mats.Clear(); propObjects.Clear(); alleyChairs.Clear(); boardForIns.Clear(); rnd = new System.Random(22);
            toon = Shader.Find("OUAT/Toon"); ground = Shader.Find("OUAT/Ground"); unlit = Shader.Find("OUAT/Unlit");
            var json = AssetDatabase.LoadAssetAtPath<UnityEngine.TextAsset>("Assets/Game/Resources/Chapter1/chapter1.json");
            data = json ? ChapterData.Parse(json.text) : new ChapterData();
            Places = new Dictionary<string, (Vector2, float)>(PlacesFallback);
            foreach (var p in data.Places.Values)
            {
                var c = J.List(p.Raw, "center");
                if (c.Count >= 2) Places[p.Id] = (new Vector2(J.F(c[0]), J.F(c[1])), p.Raw.TryGetValue("radius", out var r) ? J.F(r) : 10f);
            }
            LoadArtMaterials();
            LoadSlice();

            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            envRoot = new GameObject("Environment").transform;
            propsRoot = new GameObject("Props").transform;
            npcRoot = new GameObject("Creatures").transform;
            zoneRoot = new GameObject("Zones").transform;

            BuildLighting();
            BuildTerrain();
            Physics.SyncTransforms();
            BuildDressing();
            BuildLayoutDressing();
            BuildProps();
            Physics.SyncTransforms();
            BuildInscriptions();
            BuildReadables();
            BuildPuzzles();
            var fish = BuildFish();
            BuildZones();
            // 열고 닫히는 문·문 구멍의 코는 실행 중 장애물(NavMeshObstacle)이 맡음 — 구울 때 모형 충돌체가 틈을 영구히 막지 않게
            // 누르는 자리·크리처의 클릭용 충돌체(Use_ 상자, 인물 캡슐)도 굽기에서 뺌 — 사다리 머리 Use_pz_ladder 상자가 비탈 입구를 깎던 것 등
            foreach (var it in Object.FindObjectsByType<Interactable>(FindObjectsInactive.Include, FindObjectsSortMode.None))
                if (!it.GetComponent<NavMeshModifier>()) it.gameObject.AddComponent<NavMeshModifier>().ignoreFromBuild = true;
            foreach (var id in new[] { "bark_door", "door_nose" })
                if (propObjects.TryGetValue(id, out var go) && go && !go.GetComponent<NavMeshModifier>()) go.AddComponent<NavMeshModifier>().ignoreFromBuild = true;
            var narrow = NarrowPassageStrips();
            BakeNavMesh();
            foreach (var n in narrow) Object.DestroyImmediate(n);
            NavReport();
            var player = BuildPlayer();
            BuildNpcs();
            AttachProps(player);
            BuildSystems(player, fish);

            ProjectSetup.EnsureFolder("Assets/Game/Scenes");
            EditorSceneManager.SaveScene(scene, ScenePath);
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };
            AssetDatabase.SaveAssets();
            ReportSizes();
            Debug.Log("[OUAT] SceneBuilder done: " + ScenePath);
        }

        // ── 가져오기 설정 ───────────────────────────────────
        static void FixModelImport()
        {
            foreach (var guid in AssetDatabase.FindAssets("t:Model", new[] { ModelDir }))
            {
                var path = AssetDatabase.GUIDToAssetPath(guid);
                var mi = AssetImporter.GetAtPath(path) as ModelImporter;
                if (mi == null) continue;
                bool dirty = false;
                if (CharacterImport.IsAnimated(path))   // 뼈대·클립이 있는 캐릭터·물고기는 Legacy 애니메이션으로(CharacterImport가 맡음)
                {
                    if (mi.animationType != ModelImporterAnimationType.Legacy || !mi.importAnimation) { mi.animationType = ModelImporterAnimationType.Legacy; mi.importAnimation = true; dirty = true; }
                    if (!mi.isReadable) { mi.isReadable = true; dirty = true; }
                    if (dirty) mi.SaveAndReimport();
                    continue;
                }
                if (mi.animationType != ModelImporterAnimationType.None) { mi.animationType = ModelImporterAnimationType.None; dirty = true; }
                if (mi.importAnimation) { mi.importAnimation = false; dirty = true; }
                if (mi.materialImportMode != ModelImporterMaterialImportMode.ImportViaMaterialDescription) { mi.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription; dirty = true; }
                if (!mi.isReadable) { mi.isReadable = true; dirty = true; }
                if (dirty) mi.SaveAndReimport();
            }
        }

        static void EnsureTextureImport()
        {
            foreach (var dir in new[] { "Assets/Game/Resources/Glyphs", "Assets/Game/Resources/Pictures", "Assets/Game/Art/UI", "Assets/Game/Resources/UI" })
            {
                if (!AssetDatabase.IsValidFolder(dir)) continue;
                foreach (var guid in AssetDatabase.FindAssets("t:Texture2D", new[] { dir }))
                {
                    var path = AssetDatabase.GUIDToAssetPath(guid);
                    var ti = AssetImporter.GetAtPath(path) as TextureImporter;
                    if (ti == null) continue;
                    bool cursor = path.Contains("cursor_");
                    var want = cursor ? TextureImporterType.Cursor : TextureImporterType.Default;
                    if (ti.textureType != want || ti.mipmapEnabled || ti.textureCompression != TextureImporterCompression.Uncompressed || !ti.alphaIsTransparency)
                    {
                        ti.textureType = want; ti.mipmapEnabled = false; ti.alphaIsTransparency = true;
                        ti.textureCompression = TextureImporterCompression.Uncompressed; ti.wrapMode = TextureWrapMode.Clamp;
                        if (cursor) ti.isReadable = true;
                        ti.SaveAndReimport();
                    }
                }
            }
        }

        static void ReportSizes()
        {
            foreach (var n in new[] { "Hero_Bluebird", "Kinopio", "Chief", "Fish", "House_1", "Cliff_1", "Stage", "Tower_Dome", "Ladder", "CaveWall_1" })
            {
                var a = AssetDatabase.LoadAssetAtPath<GameObject>($"{ModelDir}/{n}.fbx");
                if (!a) continue;
                var g = Object.Instantiate(a);
                var b = Bounds(g);
                Debug.Log($"[OUAT] size {n}: {b.size.x:0.00} x {b.size.y:0.00} x {b.size.z:0.00}");
                Object.DestroyImmediate(g);
            }
        }

        // ── 재질 ─────────────────────────────────────────
        static Color Hex(string h) { ColorUtility.TryParseHtmlString(h.StartsWith("#") ? h : "#" + h, out var c); return c; }

        static Material SaveMat(string name, Shader sh)
        {
            ProjectSetup.EnsureFolder(MatDir);
            var path = $"{MatDir}/{name}.mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m == null) { m = new Material(sh); AssetDatabase.CreateAsset(m, path); }
            m.shader = sh;
            return m;
        }

        static Material Mat(string name, string baseHex, string shadeHex = null, float paint = 1f, bool outline = true, float hatch = 0.55f)
        {
            if (mats.TryGetValue(name, out var m)) return m;
            m = SaveMat(name, toon);
            var b = Hex(baseHex);
            m.SetColor("_BaseColor", b);
            m.SetColor("_ShadeColor", shadeHex != null ? Hex(shadeHex) : Color.Lerp(b, Hex("8E96A3"), 0.45f));
            m.SetFloat("_Paint", paint);
            m.SetColor("_PaperColor", paint < 0.5f ? b : Hex("F1EEE6"));
            m.SetFloat("_OutlineWidth", outline ? 0.02f : 0f);
            m.SetShaderPassEnabled("SRPDefaultUnlit", outline);   // 외곽선 없는 재질은 외곽선 단계를 아예 끔
            m.SetFloat("_Cull", outline ? 2f : 0f);               // 외곽선 없는 판(바닥·돌)은 양면
            m.SetFloat("_HatchStrength", hatch);
            EditorUtility.SetDirty(m);
            mats[name] = m;
            return m;
        }

        static Material Unlit(string name, Color c, string mode = "opaque", bool doubleSided = true)
        {
            if (mats.TryGetValue(name, out var m)) return m;
            m = SaveMat(name, unlit);
            m.SetColor("_BaseColor", c);
            m.SetFloat("_Cull", doubleSided ? 0 : 2);
            switch (mode)
            {
                case "alpha": m.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha); m.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha); m.SetFloat("_ZWrite", 0); m.renderQueue = 3000; break;
                case "add": m.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha); m.SetFloat("_DstBlend", (float)BlendMode.One); m.SetFloat("_ZWrite", 0); m.renderQueue = 3100; break;
                default: m.SetFloat("_SrcBlend", (float)BlendMode.One); m.SetFloat("_DstBlend", (float)BlendMode.Zero); m.SetFloat("_ZWrite", 1); m.renderQueue = 2000; break;
            }
            EditorUtility.SetDirty(m);
            mats[name] = m;
            return m;
        }

        static Material GroundMat(string name, float hex, string tint = null, float tintA = 0.35f)
        {
            if (mats.TryGetValue(name, out var m)) return m;
            m = SaveMat(name, ground);
            m.SetFloat("_HexAmount", hex);
            var c = tint != null ? Hex(tint) : Color.white; c.a = tint != null ? tintA : 0f; m.SetColor("_Tint", c);
            EditorUtility.SetDirty(m);
            mats[name] = m;
            return m;
        }

        /// <summary>Art/art_materials.json(3D 담당)의 이름·색·분류로 재질을 만든다.</summary>
        static void LoadArtMaterials()
        {
            var path = "Assets/Game/Art/art_materials.json";
            if (!File.Exists(path)) return;
            var root = Jigsaw.MiniJson.Parse(File.ReadAllText(path)) as Dictionary<string, object>;
            if (root == null || !(root.TryGetValue("materials", out var ms) && ms is Dictionary<string, object> md)) return;
            foreach (var kv in md)
            {
                if (!(kv.Value is Dictionary<string, object> e)) continue;
                string baseHex = J.Str(e, "base", "F1EEE6").TrimStart('#');
                string shade = J.Str(e, "shade", null)?.TrimStart('#');
                string cat = J.Str(e, "category", "painted");
                bool outline = J.Bool(e, "outline", true);
                bool hatch = J.Bool(e, "hatch", cat == "paper");
                float alpha = e.TryGetValue("alpha", out var a) ? J.F(a) : 1f;
                var col = Hex(baseHex); col.a = alpha;
                switch (cat)
                {
                    case "line": Unlit(kv.Key, col, alpha < 1f ? "alpha" : "opaque"); break;
                    case "silhouette": Unlit(kv.Key, col, "opaque", false); break;
                    case "sketch": { var m = Unlit(kv.Key, new Color(col.r, col.g, col.b, alpha < 1f ? alpha : 0.45f), "alpha"); m.SetFloat("_Wobble", 0.6f); break; }
                    case "light":
                    {
                        // 빛 웅덩이는 또렷하게, 빛줄기는 옅게(화면 가운데를 뿌옇게 가리지 않게), 옛 원뿔은 아주 옅게
                        float la2 = e.TryGetValue("alpha", out var la) ? J.F(la) * 0.5f : 0.06f;
                        if (kv.Key.Contains("Beam")) la2 = Mathf.Min(la2, 0.035f);
                        var m = Unlit(kv.Key, new Color(col.r, col.g, col.b, la2), "add");
                        m.SetFloat("_FadeUp", kv.Key.Contains("Pool") ? 1f : 0.85f);
                        break;
                    }
                    case "paper": Mat(kv.Key, baseHex, shade, 0.12f, outline, hatch ? 0.6f : 0.15f); break;
                    default:
                    {
                        var m = Mat(kv.Key, baseHex, shade, 1f, outline, hatch ? 0.45f : 0.12f);
                        if (e.TryGetValue("emission", out var em) && em is string eh) m.SetColor("_Emission", Hex(eh.TrimStart('#')) * 0.6f);
                        break;
                    }
                }
                // 땅 밑 세계 분위기(구역마다 어둑하고 색이 빠짐) — 사람 물건·주인공·빛은 색을 지킴, 밝은 선 재질(천장 등)은 같이 어두워짐
                if (mats.TryGetValue(kv.Key, out var made))
                {
                    bool keep = J.Bool(e, "keep", KeepByName(kv.Key));
                    made.SetFloat("_KeepColor", keep || cat == "light" ? 1f : 0f);
                    if (cat == "line" && col.grayscale > 0.45f) made.SetFloat("_AmbientMul", 1f);
                    EditorUtility.SetDirty(made);
                }
            }
        }

        static bool KeepByName(string n) =>
            new[] { "Bluebird", "Beak", "CapNavy", "EyeShine", "Brass", "Iron", "Rope", "M_Wood", "Leather", "Book", "PageWhite", "Porcelain", "LampGlow", "Light" }
                .Any(k => n.Contains(k));

        // ── 빛 ──────────────────────────────────────────
        static void BuildLighting()
        {
            var sun = new GameObject("Key Light").AddComponent<Light>();
            sun.type = LightType.Directional;
            sun.color = Hex("E9E6E0");
            sun.intensity = 0.95f;
            sun.shadows = LightShadows.Soft;
            sun.shadowStrength = 0.8f;
            sun.transform.rotation = Quaternion.Euler(55f, -35f, 0f);
            RenderSettings.ambientMode = AmbientMode.Flat;
            RenderSettings.ambientLight = Hex("9DA6B1");
            RenderSettings.fog = false;
            RenderSettings.skybox = null;
        }

        // ── 땅·벽·배경 ───────────────────────────────────
        static GameObject Prim(PrimitiveType t, string name, Vector3 pos, Vector3 scale, Material m, Transform parent, Vector3? euler = null)
        {
            var g = GameObject.CreatePrimitive(t);
            g.name = name; g.transform.SetParent(parent);
            g.transform.position = pos; g.transform.localScale = scale;
            if (euler.HasValue) g.transform.rotation = Quaternion.Euler(euler.Value);
            g.GetComponent<Renderer>().sharedMaterial = m;
            return g;
        }

        static void Static(GameObject g) => GameObjectUtility.SetStaticEditorFlags(g, StaticEditorFlags.BatchingStatic);

        static Vector2 C(string place) => Places.TryGetValue(place, out var p) ? p.c : Vector2.zero;

        static bool BuildLevel()
        {
            var asset = AssetDatabase.LoadAssetAtPath<GameObject>($"{ModelDir}/Level_Ch1.fbx");
            if (!asset) return false;
            var g = (GameObject)PrefabUtility.InstantiatePrefab(asset, envRoot);
            PrefabUtility.UnpackPrefabInstance(g, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
            RemapMaterials(g);
            foreach (var mf in g.GetComponentsInChildren<MeshFilter>())
            {
                // 구역별 묶음(Area_<id> / Global) 아래의 부품 이름으로 판단(블렌더 3차: Ground_Walk_fall 등)
                var top = mf.transform;
                while (top.parent && top.parent != g.transform && !top.parent.name.StartsWith("Area_") && !top.parent.name.StartsWith("Global")) top = top.parent;
                string part = top.name;
                var r = mf.GetComponent<Renderer>();
                bool collide = part.StartsWith("Ground_Walk") || part.StartsWith("Cliffs") || part.StartsWith("Walls_Bound");
                if (collide) { var mc = mf.gameObject.AddComponent<MeshCollider>(); mc.sharedMesh = mf.sharedMesh; Static(mf.gameObject); }
                // 절벽·경계벽은 클릭만 받고 길 찾기 영역 굽기에서는 뺌 — 구역끼리 공간이 겹쳐 다른 구역 절벽이 굴 입구 바닥을 깎던 문제(10/23 NAV 검사). 걷는 범위는 Ground_Walk 가장자리가 정함
                if (part.StartsWith("Cliffs") || part.StartsWith("Walls_Bound")) { var nm = mf.gameObject.AddComponent<NavMeshModifier>(); nm.ignoreFromBuild = true; }
                if (part.StartsWith("Ground_Lines") || part.StartsWith("Ceiling") || part.StartsWith("Backdrop")) { if (r) r.shadowCastingMode = ShadowCastingMode.Off; }
                if (part.StartsWith("Ground_Lines") && r) r.receiveShadows = false;
                if ((part.StartsWith("Vista") || part.StartsWith("Light_")) && r) { r.shadowCastingMode = ShadowCastingMode.Off; r.receiveShadows = !part.StartsWith("Light_"); }
                if ((part.StartsWith("Margin") || part.StartsWith("Exit_") || part.StartsWith("Light_")) && r) { r.shadowCastingMode = ShadowCastingMode.Off; var mod = mf.gameObject.AddComponent<NavMeshModifier>(); mod.ignoreFromBuild = true; }
            }
            return true;
        }

        static void BuildTerrain()
        {
            if (BuildLevel()) return;
            var outskirt = GroundMat("G_Outskirt", 0f);
            var paved = GroundMat("G_Paved", 0.55f);
            var plazaPaint = GroundMat("G_PlazaPainted", 1f, "D7B590", 0.4f);
            var fieldMat = GroundMat("G_Field", 0f, "C9B79A", 0.35f);

            var floor = Prim(PrimitiveType.Cube, "Floor", new Vector3(0, -0.5f, 5), new Vector3(190, 1, 140), outskirt, envRoot);
            Static(floor);

            // 큰길(선으로 그린 육각 돌길)
            string[] main = { "fall", "gate", "plaza", "alley", "field", "pond" };
            Road(new Vector2(-44.5f, 25.5f), C("gate"), 5f, paved, "Road_fall_gate");
            for (int i = 1; i < main.Length - 1; i++) Road(C(main[i]), C(main[i + 1]), 5.5f, paved, "Road_" + main[i] + "_" + main[i + 1]);
            // 수레 길(광장 남쪽으로 돎, 데이터 z_fence route)
            var cart = new[] { new Vector2(-44, 22), new Vector2(-36, 4), new Vector2(-28, -4), new Vector2(0, -10), new Vector2(30, -8), new Vector2(36, -5) };
            for (int i = 0; i < cart.Length - 1; i++) Road(cart[i], cart[i + 1], 3.2f, outskirt, "CartRoad_" + i);

            var plaza = Prim(PrimitiveType.Cylinder, "Plaza_Disc", new Vector3(C("plaza").x, -0.47f, C("plaza").y), new Vector3(34, 0.5f, 34), plazaPaint, envRoot);
            Object.DestroyImmediate(plaza.GetComponent<Collider>()); plaza.AddComponent<MeshCollider>(); Static(plaza);
            var field = Prim(PrimitiveType.Cylinder, "Field_Disc", new Vector3(C("field").x, -0.48f, C("field").y), new Vector3(30, 0.5f, 26), fieldMat, envRoot);
            Object.DestroyImmediate(field.GetComponent<Collider>()); field.AddComponent<MeshCollider>(); Static(field);

            // 빛구멍 언덕: 높은 원판(사방이 절벽, 동쪽 끝 사다리 자리만 내려감)
            var fall = C("fall");
            var mesa = Prim(PrimitiveType.Cylinder, "Fall_Mesa", new Vector3(fall.x, MesaHeight / 2f - 0.02f, fall.y), new Vector3(25, MesaHeight / 2f, 25), GroundMat("G_Mesa", 0.5f), envRoot);
            Object.DestroyImmediate(mesa.GetComponent<Collider>()); mesa.AddComponent<MeshCollider>(); Static(mesa);
            for (int i = 0; i < 18; i++)
            {
                float a = i / 18f * Mathf.PI * 2f;
                var p = new Vector3(fall.x + Mathf.Cos(a) * 12.8f, MesaHeight, fall.y + Mathf.Sin(a) * 12.8f);
                var cl = Model("Cliff_" + (1 + i % 3), p, -a * Mathf.Rad2Deg + 90f, envRoot, 0.85f, keepColliders: false);
                Static(cl);
            }
            // 사다리가 펴지면 걷는 비탈(사다리 자리, 언덕 동쪽 끝 → 아래)
            var ladderTop = new Vector3(-45.5f, MesaHeight, 27.4f);
            var ladderBottom = new Vector3(-41.5f, 0f, 23.8f);
            var rampGo = Prim(PrimitiveType.Cube, "LadderRamp", (ladderTop + ladderBottom) / 2f + Vector3.up * -0.05f, new Vector3(1.6f, 0.15f, Vector3.Distance(ladderTop, ladderBottom) + 0.6f), GroundMat("G_Mesa", 0.5f), envRoot);
            rampGo.transform.rotation = Quaternion.LookRotation(ladderBottom - ladderTop);
            rampGo.GetComponent<Renderer>().enabled = false;

            // 동굴 벽(그리다 만 선)
            for (int i = 0; i < 34; i++)
            {
                float a = i / 34f * Mathf.PI * 2f;
                var p = new Vector3(Mathf.Cos(a) * 88f, 0f, 6 + Mathf.Sin(a) * 64f);
                var w = Model("CaveWall_" + (1 + i % 3), p, -a * Mathf.Rad2Deg - 90f, envRoot, 1.3f + (float)rnd.NextDouble() * 0.6f, keepColliders: false);
                Static(w);
            }
            // 배경 첨탑
            for (int i = 0; i < 26; i++)
            {
                float a = (float)rnd.NextDouble() * Mathf.PI * 2f;
                float r = 96f + (float)rnd.NextDouble() * 30f;
                var s = Model("Spire_" + (1 + i % 3), new Vector3(Mathf.Cos(a) * r, -1, 6 + Mathf.Sin(a) * r * 0.8f), (float)rnd.NextDouble() * 360f, envRoot, 1.6f + (float)rnd.NextDouble() * 1.6f, keepColliders: false);
            }
            // 천장 구멍
            Model("CeilingHole", new Vector3(fall.x, 30f, fall.y), 0, envRoot, 1f, keepColliders: false);
        }

        static void Road(Vector2 a, Vector2 b, float width, Material m, string name)
        {
            var mid = (a + b) / 2f; var d = b - a;
            var g = Prim(PrimitiveType.Cube, name, new Vector3(mid.x, -0.48f, mid.y), new Vector3(width, 0.5f, d.magnitude + width * 0.6f), m, envRoot, new Vector3(0, Mathf.Atan2(d.x, d.y) * Mathf.Rad2Deg, 0));
            Static(g);
        }

        // ── 모델 ─────────────────────────────────────────
        static GameObject Model(string name, Vector3 pos, float yaw, Transform parent, float scale = 1f, bool keepColliders = true)
        {
            var asset = AssetDatabase.LoadAssetAtPath<GameObject>($"{ModelDir}/{name}.fbx") ?? AssetDatabase.LoadAssetAtPath<GameObject>($"{ModelDir}/{name}.prefab");
            GameObject g;
            if (asset)
            {
                g = (GameObject)PrefabUtility.InstantiatePrefab(asset, parent);
                PrefabUtility.UnpackPrefabInstance(g, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
                RemapMaterials(g);
            }
            else
            {
                g = new GameObject(name + " (임시)");
                g.transform.SetParent(parent);
                var c = GameObject.CreatePrimitive(PrimitiveType.Cube); c.transform.SetParent(g.transform, false); c.transform.localPosition = Vector3.up * 0.5f;
                c.GetComponent<Renderer>().sharedMaterial = Mat("M_Paper", "F1EEE6");
                Debug.LogWarning("[OUAT] 모델 없음: " + name);
            }
            g.transform.position = pos;
            g.transform.rotation = Quaternion.Euler(0, yaw, 0);
            g.transform.localScale *= scale;
            if (keepColliders) AddMeshColliders(g);
            return g;
        }

        static void AddMeshColliders(GameObject g)
        {
            foreach (var mf in g.GetComponentsInChildren<MeshFilter>())
            {
                if (mf.GetComponent<Collider>()) continue;
                var r = mf.GetComponent<Renderer>();
                if (r && r.sharedMaterials.Any(m => m && m.shader == unlit)) continue;
                var mc = mf.gameObject.AddComponent<MeshCollider>();
                mc.sharedMesh = mf.sharedMesh;
            }
        }

        static void RemapMaterials(GameObject g)
        {
            foreach (var r in g.GetComponentsInChildren<Renderer>())
            {
                var shared = r.sharedMaterials;
                for (int i = 0; i < shared.Length; i++)
                {
                    var n = shared[i] ? shared[i].name.Replace(" (Instance)", "").Split('.')[0] : "M_Paper";
                    if (!mats.TryGetValue(n, out var m)) m = Mat(n, GuessColor(n), null, n.Contains("Paper") ? 0.12f : 1f, true);
                    shared[i] = m;
                }
                r.sharedMaterials = shared;
                r.shadowCastingMode = shared.Any(m => m && m.shader == unlit) ? ShadowCastingMode.Off : ShadowCastingMode.On;
            }
        }

        static string GuessColor(string n)
        {
            n = n.ToLowerInvariant();
            if (n.Contains("blue")) return "2F5FD0";
            if (n.Contains("ink") || n.Contains("silhou")) return "2B2622";
            if (n.Contains("brass")) return "C8902E";
            if (n.Contains("iron")) return "6E7681";
            if (n.Contains("red") || n.Contains("rope") || n.Contains("curtain")) return "C2452F";
            if (n.Contains("fish")) return "243B3F";
            if (n.Contains("wood")) return "E8C99A";
            if (n.Contains("terra")) return "C98A55";
            return "F1EEE6";
        }

        static Bounds Bounds(GameObject g)
        {
            var rs = g.GetComponentsInChildren<Renderer>();
            if (rs.Length == 0) return new Bounds(g.transform.position, Vector3.one);
            var b = rs[0].bounds;
            foreach (var r in rs) b.Encapsulate(r.bounds);
            return b;
        }

        static Transform FindPart(GameObject g, string name)
        {
            foreach (var t in g.GetComponentsInChildren<Transform>(true))
                if (t != g.transform && (t.name == name || t.name.StartsWith(name + ".") || t.name.StartsWith(name + "_"))) return t;
            return null;
        }

        static Vector3 Ground(Vector2 xz, float add = 0f)
        {
            if (Physics.Raycast(new Vector3(xz.x, 50, xz.y), Vector3.down, out var hit, 100f, ~0, QueryTriggerInteraction.Ignore)) return hit.point + Vector3.up * add;
            return new Vector3(xz.x, add, xz.y);
        }
        static Vector3 Ground(Vector3 p, float add = 0f) => Ground(new Vector2(p.x, p.z), add);

        static float YawToward(Vector2 from, Vector2 to) { var d = to - from; return Mathf.Atan2(d.x, d.y) * Mathf.Rad2Deg; }

        // ── 마을 꾸밈(데이터 밖 배경) ───────────────────────
        static void BuildDressing()
        {
            if (slice.ContainsKey("alley_seated_lumps")) { BuildSlice2Dressing(); return; }
            // 광장: 칠해진 테라코타 돔 탑(다 그려진 쪽 = 안쪽·왕에 가까운 곳)
            var plaza = C("plaza");
            Model("Tower_Dome", Ground(plaza + (slice.Count > 0 ? new Vector2(-12, 20) : new Vector2(-17, 18))), 160, propsRoot, 1.1f);   // 길목 구역에 잡혀 문 앞을 막지 않게(지형 담당 10/23)
            Model("Tower_Dome", Ground(plaza + new Vector2(17, 20)), 200, propsRoot, 1.25f);
            Model("Tower_Dome", Ground(plaza + new Vector2(30, 30)), 220, propsRoot, 0.9f);
            for (int i = 0; i < 5; i++)
            {
                var p = plaza + new Vector2(-12 + i * 6f, i % 2 == 0 ? -4 : 2);
                if (i == 2) continue;
                var lp = Model("LampPost", Ground(p), 0, propsRoot);
                var l = new GameObject("Lamp").AddComponent<Light>();
                l.transform.SetParent(lp.transform, false); l.transform.localPosition = new Vector3(-0.38f, 2.6f, 0);
                l.type = LightType.Point; l.color = Hex("FFC870"); l.intensity = 5f; l.range = 8f; l.shadows = LightShadows.None;
            }
            // 골목·길가의 집들(바깥일수록 덜 칠함)
            var alley = C("alley");
            for (int i = 0; i < 6; i++)
            {
                float dx = -10 + i * 4.4f, dz = i % 2 == 0 ? 6.8f : -9.8f;
                var h = Model("House_" + (1 + i % 4), Ground(alley + new Vector2(dx, dz)), dz > 0 ? 180 : 0, propsRoot);
                Static(h);
            }


            // 언덕 위 떨어진 사람 물건들
            string[] junk = { "Junk_Book", "Junk_Umbrella", "Junk_Clock", "Junk_Shoe", "Junk_Teacup", "Junk_Lantern" };
            var fall = C("fall");
            if (slice.TryGetValue("fall_junk", out var fj) && fj is List<object> fjl)
            {
                foreach (var o in fjl.OfType<Dictionary<string, object>>())
                {
                    var pp = J.List(o, "pos");
                    Model(J.Str(o, "model"), Ground(new Vector2(J.F(pp[0]), J.F(pp[1]))), o.TryGetValue("yaw", out var yy) ? J.F(yy) : 0f, propsRoot, o.TryGetValue("scale", out var ss) ? J.F(ss) : 1f, keepColliders: false);
                }
                return;
            }
            for (int i = 0; i < 30; i++)
            {
                float a = (float)rnd.NextDouble() * 6.28f, r = 1.5f + (float)rnd.NextDouble() * 8f;
                Model(junk[i % junk.Length], Ground(fall + new Vector2(Mathf.Cos(a) * r, Mathf.Sin(a) * r)), (float)rnd.NextDouble() * 360f, propsRoot, 0.9f + (float)rnd.NextDouble() * 0.5f, keepColliders: false);
            }
        }

        /// <summary>art/layout_dressing.json(블렌더 담당)의 꾸밈 배치. 높이는 아래로 쏘아 땅에 맞춘다.</summary>
        static void BuildLayoutDressing()
        {
            var path = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "art", "layout_dressing.json"));
            if (!File.Exists(path)) return;
            var root = Jigsaw.MiniJson.Parse(File.ReadAllText(path)) as Dictionary<string, object>;
            var dress = new GameObject("Dressing").transform;
            foreach (var o in J.List(root, "items").OfType<Dictionary<string, object>>())
            {
                var pos = J.List(o, "pos");
                if (pos.Count < 2) continue;
                var name = J.Str(o, "model");
                float yaw = o.TryGetValue("yaw", out var y) ? J.F(y) : 0f, sc = o.TryGetValue("scale", out var s) ? J.F(s) : 1f;
                bool collide = !(name.StartsWith("Scrap") || name.StartsWith("FX_") || name.StartsWith("Sketch_Tree") || name.StartsWith("Banner") || name.StartsWith("Lantern"));
                var gp = Ground(new Vector2(J.F(pos[0]), J.F(pos[1])));
                if (o.TryGetValue("y", out var oy) && Mathf.Abs(gp.y - J.F(oy)) > 1.5f) gp.y = J.F(oy);   // 레이캐스트가 엉뚱한 층에 닿으면 기대 높이로
                var g = Model(name, gp, yaw, dress, sc, keepColliders: collide);
                if (name.StartsWith("LampPost"))
                {
                    var ll = new GameObject("Lamp").AddComponent<Light>();
                    ll.transform.SetParent(g.transform, false); ll.transform.localPosition = new Vector3(-0.38f, 2.6f, 0);
                    ll.type = LightType.Point; ll.color = Hex("FFC870"); ll.intensity = 4f; ll.range = 7f; ll.shadows = LightShadows.None;
                }
                if (name.StartsWith("Lantern"))
                {
                    var l = new GameObject("Lamp").AddComponent<Light>();
                    l.transform.SetParent(g.transform, false); l.transform.localPosition = new Vector3(0, 0.2f, 0);
                    l.type = LightType.Point; l.color = Hex("FFC870"); l.intensity = 3f; l.range = 6f; l.shadows = LightShadows.None;
                }
            }
        }

        /// <summary>2차 지형(art/layout_slice2.json): 광장 탑·등·골목 집은 layout_dressing.json이 맡고, 여기선 의자 위 천 덮은 덩어리·굴의 숨긴 물건·언덕 잡동사니.</summary>
        static void BuildSlice2Dressing()
        {
            var root = new GameObject("SeatedLumps").transform; root.SetParent(propsRoot);
            foreach (var o in J.List(slice, "alley_seated_lumps").OfType<Dictionary<string, object>>())
            {
                var c = J.List(o, "chair"); var cp = Ground(new Vector2(J.F(c[0]), J.F(c[1])));
                float yaw = J.F(o["yaw"]), sy = o.TryGetValue("seat_y", out var s) ? J.F(s) : 0.5f;
                var chair = Model("Chair", cp, yaw, root);
                alleyChairs.Add(chair.transform);
                var l = Model(J.Str(o, "lump", "Lump_1"), cp + Vector3.up * sy, yaw, chair.transform, 1f, keepColliders: false);
                l.name = "Lump";
                Cover(l, cp + Vector3.up * sy, yaw);   // 2-3 “천을 덮은 덩어리”
            }
            // 형 덩어리는 데이터 물건 brother_lump가 맡음(천 덮개를 걷는 상태가 있음) — 없을 때만 옛 꾸밈
            if (!data.Props.ContainsKey("brother_lump") && slice.TryGetValue("kid_house_chair", out var kc) && kc is Dictionary<string, object> kcd)
            {
                var c = J.List(kcd, "chair"); var cp = Ground(new Vector2(J.F(c[0]), J.F(c[1])));
                Model("Chair", cp, J.F(kcd["yaw"]), root);
                Model("Lump_Brother", cp + Vector3.up * 0.5f, J.F(kcd["yaw"]), root, 1f, keepColliders: false).name = "BrotherLump";
            }
            foreach (var o in J.List(slice, "hideout_stash").OfType<Dictionary<string, object>>())
            {
                var pp = J.List(o, "pos"); float y = o.TryGetValue("y", out var yy) ? J.F(yy) : 0f;
                var at = new Vector3(J.F(pp[0]), y, J.F(pp[1]));
                var name = J.Str(o, "model");
                var g = Model(name, at, o.TryGetValue("yaw", out var yw) ? J.F(yw) : 0f, propsRoot, o.TryGetValue("scale", out var sc) ? J.F(sc) : 1f, keepColliders: false);
                if (name.StartsWith("Junk_Lantern")) PointLight(g.transform, new Vector3(0, 0.3f, 0), "FFB866", 4f, 4f);
            }
            // 3차 다듬기의 작은 불빛(죽 가게 불·이웃 창 등)
            if (slice.TryGetValue("lights3", out var l3) && l3 is Dictionary<string, object> l3d)
                foreach (var kv in l3d)
                {
                    if (!(kv.Value is Dictionary<string, object> ld) || !ld.ContainsKey("pos")) continue;
                    var lp = J.List(ld, "pos"); var gp = Ground(new Vector2(J.F(lp[0]), J.F(lp[1])));
                    var lt = new GameObject("Light_" + kv.Key).AddComponent<Light>(); lt.transform.SetParent(propsRoot);
                    lt.transform.position = gp + Vector3.up * (ld.TryGetValue("height", out var hh) ? J.F(hh) : 1.2f);
                    lt.type = LightType.Point; lt.color = Hex(J.Str(ld, "color", "FFC870")); lt.range = ld.TryGetValue("range", out var rr) ? J.F(rr) : 3f;
                    lt.intensity = ld.TryGetValue("intensity_hint", out var ih) ? J.F(ih) * 2f : 3f; lt.shadows = LightShadows.None;
                }
            // 언덕 잡동사니(1차 지형 목록)
            if (slice.TryGetValue("fall_junk", out var fj) && fj is List<object> fjl)
                foreach (var o in fjl.OfType<Dictionary<string, object>>())
                {
                    var pp = J.List(o, "pos");
                    Model(J.Str(o, "model"), Ground(new Vector2(J.F(pp[0]), J.F(pp[1]))), o.TryGetValue("yaw", out var yy) ? J.F(yy) : 0f, propsRoot, o.TryGetValue("scale", out var ss) ? J.F(ss) : 1f, keepColliders: false);
                }
        }

        /// <summary>의자 위 덩어리를 덮는 천(ClothCover, 루트 = 앉는 면). 모델이 없으면 납작한 공에 자루천.</summary>
        static GameObject Cover(GameObject lump, Vector3 seat, float yaw)
        {
            GameObject c;
            if (HasModel("ClothCover")) c = Model("ClothCover", seat, yaw, lump.transform, 1f, keepColliders: false);
            else
            {
                var b = Bounds(lump);
                c = Prim(PrimitiveType.Sphere, "Cover", b.center + Vector3.up * 0.03f, new Vector3(b.size.x * 1.25f, b.size.y * 1.2f, b.size.z * 1.25f), MatOr("M_Sackcloth", "CDBB9A"), lump.transform);
                Object.DestroyImmediate(c.GetComponent<Collider>());
            }
            c.name = "Cover";
            return c;
        }

        static bool HasModel(string n) => AssetDatabase.LoadAssetAtPath<GameObject>($"{ModelDir}/{n}.fbx") != null;
        static Material MatOr(string name, string hex) => mats.TryGetValue(name, out var m) ? m : Mat(name, hex);

        static Light PointLight(Transform parent, Vector3 local, string hex, float intensity, float range, string name = "Lamp")
        {
            var l = new GameObject(name).AddComponent<Light>();
            l.transform.SetParent(parent, false); l.transform.localPosition = local;
            l.type = LightType.Point; l.color = Hex(hex); l.intensity = intensity; l.range = range; l.shadows = LightShadows.None;
            return l;
        }

        static GameObject Group(string name, Vector3 pos, float yaw = 0f, Transform parent = null)
        {
            var g = new GameObject(name);
            g.transform.SetParent(parent ? parent : propsRoot);
            g.transform.position = pos; g.transform.rotation = Quaternion.Euler(0, yaw, 0);
            return g;
        }

        /// <summary>Level_Ch1 안의 따로 된 부품(Bell_plaza·Satchel_cart·Face_hideout).</summary>
        static Transform LevelPart(string name) => envRoot ? envRoot.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == name || t.name.StartsWith(name + ".")) : null;

        static Vector2 ZoneXZ(string id, Vector2 fallback) => data.Zones.TryGetValue(id, out var z) ? z.Pos : fallback;
        static Vector2? ExitXZ(string area, string to, bool spawn = false)
        {
            if (!data.Areas.TryGetValue(area, out var a)) return null;
            var e = a.Exits.FirstOrDefault(x => x.To == to);
            return e == null ? (Vector2?)null : spawn ? e.Spawn : e.Pos;
        }

        /// <summary>물건 앞면(로컬 +Z)의 그 높이 점 — 덩어리 목에 붉은 끈 붙이기 등.</summary>
        static Vector3 FrontTop(GameObject g, float heightFrac)
        {
            var b = Bounds(g);
            return FrontPoint(g, g.transform, b.min.y + b.size.y * heightFrac);
        }

        static float KidHouseYaw() => slice.TryGetValue("kid_house", out var kh) && kh is Dictionary<string, object> khd ? J.F(khd["yaw"]) : 250f;

        /// <summary>물건의 렌더러 경계를 space의 로컬 좌표로(돌아간 판·띠의 누름 상자를 맞게).</summary>
        static Bounds LocalBounds(GameObject g, Transform space)
        {
            bool any = false; var lb = new Bounds();
            foreach (var r in g.GetComponentsInChildren<Renderer>(true))
            {
                Bounds rb; Matrix4x4 m;
                if (r is SkinnedMeshRenderer sk && sk.sharedMesh) { rb = sk.sharedMesh.bounds; m = sk.transform.localToWorldMatrix; }
                else if (r.GetComponent<MeshFilter>() is MeshFilter mf && mf.sharedMesh) { rb = mf.sharedMesh.bounds; m = r.transform.localToWorldMatrix; }
                else continue;
                for (int i = 0; i < 8; i++)
                {
                    var c = rb.center + Vector3.Scale(rb.extents, new Vector3((i & 1) == 0 ? -1 : 1, (i & 2) == 0 ? -1 : 1, (i & 4) == 0 ? -1 : 1));
                    var p = space.InverseTransformPoint(m.MultiplyPoint3x4(c));
                    if (!any) { lb = new Bounds(p, Vector3.zero); any = true; } else lb.Encapsulate(p);
                }
            }
            return any ? lb : new Bounds(Vector3.up * 0.5f, Vector3.one);
        }

        // ── 데이터 물건(props) ───────────────────────────
        // 데이터 model보다 새로 온 모델이 있으면 그것(블렌더 10/23)
        static readonly Dictionary<string, (string model, float scale)> NewModels = new Dictionary<string, (string, float)>
        {
            { "music_box", ("MusicBox", 1.5f) }, { "mirror_shard", ("MirrorShard", 1.5f) }, { "spin_top", ("SpinTop", 1.6f) },
            { "cord_basket", ("CordBasket", 1f) },
        };
        // 길찾기 판을 막아야 하는 물건(그 밖은 콜라이더가 있어도 굽지 않음 — 움직이거나 숨는 물건이 구멍을 남기지 않게)
        static readonly HashSet<string> NavSolid = new HashSet<string> { "stage", "gate_stone", "fish_prop", "pond", "pond_stone", "fall_pile", "board", "sign" };

        static GameObject PropObject(PropDef p)
        {
            var at = new Vector2(p.Pos.x, p.Pos.y);
            bool hasFacing = p.Raw.TryGetValue("facing", out var f);
            float facing = hasFacing ? J.F(f) : 0f;
            GameObject g = null;
            List<GameObject> linked = null;
            if (p.Raw.ContainsKey("attach")) g = Group("Prop_" + p.Id, Ground(at));   // 인물에 붙는 물건: 인물을 만든 뒤 AttachProps가 채움
            else switch (p.Id)
            {
                case "fall_pile": g = Model("ItemPile", Ground(at), 20, propsRoot, 1.8f); break;
                case "light_beam":
                {
                    // 지형에 빛 웅덩이·빛줄기(Light_fall)가 있으면 옛 원뿔(LightShaft)은 쓰지 않음 — 화면 전체를 뿌옇게 덮음
                    g = slice.Count > 0 ? new GameObject("LightShaft (Level Light_fall)") : Model("LightShaft", new Vector3(at.x, MesaHeight - 0.05f, at.y), 0, propsRoot, 1f, keepColliders: false);
                    if (slice.Count > 0) { g.transform.SetParent(propsRoot); g.transform.position = new Vector3(at.x, MesaHeight, at.y); }
                    var spot = new GameObject("Shaft Light").AddComponent<Light>();
                    spot.transform.SetParent(g.transform, false);
                    spot.type = LightType.Spot; spot.color = Hex("FFE9C4"); spot.intensity = 520f; spot.range = 48f; spot.spotAngle = slice.Count > 0 ? 15f : 34f; spot.innerSpotAngle = 6f; spot.shadows = LightShadows.Soft;
                    spot.transform.localPosition = new Vector3(0, 30, 0); spot.transform.localRotation = Quaternion.Euler(90, 0, 0);
                    break;
                }
                case "ladder":
                {
                    var top = SliceV3("ladder_top", new Vector3(-45.6f, MesaHeight, 27.4f)); var bottom = SliceV3("ladder_bottom", new Vector3(-41.5f, 0f, 23.8f));
                    g = Model("Ladder", top, 0, propsRoot);
                    var down = (bottom - top).normalized;
                    var side = Vector3.Cross(Vector3.up, down).normalized;
                    if (slice.Count > 0)
                    {
                        // 걸쇠(앞 +Z)가 위로 보이게 Cross(down, side), 길이 방향(로컬 Y)만 늘려 비탈을 덮음
                        g.transform.rotation = Quaternion.LookRotation(Vector3.Cross(down, side), down);
                        float ls = slice.TryGetValue("ladder_scale_length_only", out var lso) ? J.F(lso) : 1f;
                        g.transform.localScale = new Vector3(1.1f, ls, 1.1f);
                        if (slice.TryGetValue("ladder_blocker", out var lb) && lb is Dictionary<string, object> lbd)
                        {
                            var bp = J.List(lbd, "pos"); var bs = J.List(lbd, "size");
                            Blocker(g.transform, new Vector3(J.F(bp[0]), J.F(bp[1]), J.F(bp[2])), new Vector3(J.F(bs[0]), J.F(bs[1]), J.F(bs[2])), J.F(lbd["yaw"]));
                        }
                    }
                    else
                    {
                        g.transform.rotation = Quaternion.LookRotation(Vector3.Cross(side, down), down) * Quaternion.Euler(-6, 0, 0);
                        var gap = Model("Gap", Ground(new Vector2(-47.4f, 25.2f)) - Vector3.up * 1.4f, YawToward(new Vector2(-47.4f, 25.2f), C("gate")), propsRoot);
                        Static(gap);
                        Blocker(g.transform, new Vector3(-43.2f, 0f, 25.4f), new Vector3(4.0f, 3.0f, 1.6f), YawToward(new Vector2(-45.6f, 27.4f), new Vector2(-41.5f, 23.8f)));
                    }
                    break;
                }
                case "bolt_fall":
                {
                    float by = slice.TryGetValue("bolt_fall", out var bf) && bf is Dictionary<string, object> bfd ? J.F(bfd["yaw"]) : YawToward(at, C("gate")) + 90;
                    g = Model("DrawnBar", Ground(at), by, propsRoot);
                    Blocker(g.transform, Ground(at), new Vector3(2.6f, 2.5f, 1.2f), by);
                    break;
                }
                case "sack":
                {
                    // 수거꾼 자루: closed = 주인공을 담은 자루(Sack), open = 열려 주저앉은 자루(Sack_Open)
                    g = Group("Sack", Ground(at), facing);
                    Model("Sack", g.transform.position, facing, g.transform, 1f, keepColliders: false).name = "state_closed";
                    Model("Sack_Open", g.transform.position, facing, g.transform, 1f, keepColliders: false).name = "state_open";
                    break;
                }
                case "gate_stone": g = Model("StoneTablet", Ground(at), hasFacing ? facing : YawToward(at, C("gate")) + 180, propsRoot); break;
                case "stage":
                {
                    var spl = slice.TryGetValue("stage_place", out var spo) ? spo as Dictionary<string, object> : null;
                    if (spl != null) { var sp0 = J.List(spl, "pos"); g = Model("Stage", Ground(new Vector2(J.F(sp0[0]), J.F(sp0[1]))), J.F(spl["yaw"]), propsRoot); }
                    else g = Model("Stage", Ground(new Vector2(at.x, at.y + 2.4f)), 180, propsRoot);
                    var sp = FindPart(g, "StageProp"); if (sp) sp.gameObject.SetActive(false);
                    PointLight(g.transform, new Vector3(0, 4.2f, 1f), "FFB860", 10f, 12f, "StageLamp").gameObject.SetActive(false);
                    break;
                }
                case "fish_prop": g = Model("FishProp", Ground(at, 0.9f), hasFacing ? facing : 180, propsRoot); break;
                case "lump_prop":
                {
                    // 극 소품: 의자 + 붉은 끈 맨 덩어리
                    float y = hasFacing ? facing : 180;
                    g = Group("StageLump", Ground(at), y);
                    Model("Chair", g.transform.position, y, g.transform);
                    var lump = Model(HasModel("Lump_4") ? "Lump_4" : "Lump_1", g.transform.position + Vector3.up * 0.5f, y, g.transform);
                    Model("RedCord", FrontTop(lump, 0.8f), y, g.transform, 1f, keepColliders: false);
                    break;
                }
                case "board":
                    g = Group("PictureBoards", Ground(at));
                    BuildPictureBoards(g.transform);
                    break;
                case "bell":
                {
                    // 광장 종 = Level의 Bell_plaza(피벗 = 매단 점)를 물건 밑으로 옮김. 없으면 Bell 모델(BellBody)
                    var part = LevelPart("Bell_plaza");
                    if (part) { g = Group("Bell", part.position); part.SetParent(g.transform, true); }
                    else g = Model("Bell", Ground(at), facing, propsRoot, 1f, keepColliders: false);
                    break;
                }
                case "band_new":
                {
                    // 4-2 새 띠(DecreeOpen): 그림판3(ins_board_chair 자리) 앞면에 붙음. Face = 크리처 띠, HumanText = 밑의 사람 글
                    var board = boardForIns.Values.OrderBy(b => Vector2.Distance(new Vector2(b.transform.position.x, b.transform.position.z), at)).FirstOrDefault();
                    g = Model(J.Str(p.Raw, "model", "DecreeOpen"), Ground(at), facing, propsRoot, 1.6f, keepColliders: false);
                    if (board && Vector2.Distance(new Vector2(board.transform.position.x, board.transform.position.z), at) < 1.5f)
                    {
                        var face = FindPart(board, "Face");
                        var fb = face && face.GetComponent<Renderer>() ? face.GetComponent<Renderer>().bounds : Bounds(board);
                        g.transform.rotation = board.transform.rotation * Quaternion.Euler(90, 0, 0);   // 띠 윗면(+Y)이 그림판 앞(+Z)을 봄
                        g.transform.position = fb.center + Vector3.up * fb.extents.y * 0.35f + board.transform.forward * 0.03f;
                    }
                    ApplyPicture(g, "decree_band");
                    ApplyPicture(g, "decree_human", 1f, "HumanText");
                    break;
                }
                case "sawdust_trail":
                {
                    // 3-2 뒤 관객석 → 광장→골목 출구까지 띄엄띄엄 부스러기(구역마다 따로 보이게 물건 밖에 둠)
                    g = Group("SawdustTrail", Ground(at));
                    var from = ZoneXZ("z_audience_seat", at); var to = ExitXZ("a_plaza", "a_alley") ?? C("alley");
                    var trail = Group("SawdustTrail_Bits", Ground(from));
                    PlaceAlong(trail.transform, new[] { (from, to) }, 1.7f, 0.35f, HasModel("SawdustBits") ? "SawdustBits" : "SawdustPile", HasModel("SawdustBits") ? 0.9f : 0.3f, false);
                    linked = new List<GameObject> { trail };
                    break;
                }
                case "torches":
                {
                    // 4-2 덜 그려진 횃불 줄: 광장(종) → 수레 길 → 밭 길(웅덩이 앞)
                    g = Group("Torches", Ground(at));
                    var row = Group("Torches_Row", Ground(at));
                    var segs = new List<(Vector2, Vector2)>();
                    var pc = ExitXZ("a_plaza", "a_cart"); var cs = ExitXZ("a_plaza", "a_cart", true); var cf = ExitXZ("a_cart", "a_field"); var fs = ExitXZ("a_cart", "a_field", true);
                    if (pc.HasValue) segs.Add((ZoneXZ("z_bell", at), pc.Value));
                    if (cs.HasValue && cf.HasValue) segs.Add((cs.Value, cf.Value));
                    if (fs.HasValue) segs.Add((fs.Value, ZoneXZ("z_pond_stop", C("field"))));
                    PlaceAlong(row.transform, segs, 4.6f, 1.5f, HasModel("Torch") ? "Torch" : "LampPost", HasModel("Torch") ? 1f : 0.7f, true);
                    linked = new List<GameObject> { row };
                    break;
                }
                case "cart":
                {
                    bool depot = slice.ContainsKey("satchel");   // 2차 지형: 수레는 창고 마당, 동쪽 길을 봄
                    g = Model("Cart", Ground(at), depot ? (hasFacing ? facing : 90f) : YawToward(at, new Vector2(54, -15)), propsRoot);
                    var hasPile = HasModel("OfferingPile");
                    var items = hasPile ? Model("OfferingPile", g.transform.TransformPoint(new Vector3(0, 0.80f, -0.10f)), g.transform.eulerAngles.y, g.transform, 1f, keepColliders: false)
                                        : Model("ItemPile", g.transform.position + Vector3.up * 0.7f, 0, g.transform, 0.55f, keepColliders: false);
                    items.name = "Items";
                    break;
                }
                case "satchel":
                {
                    // 대본대로 수레 꼭대기 가방, 끈이 바퀴 고정쇠에 물림(창고 기둥 고리의 Level Satchel_cart를 옮겨 씀)
                    var cart = propObjects.TryGetValue("cart", out var cg) ? cg : null;
                    var items = cart ? FindPart(cart, "Items") : null; var lk = cart ? FindPart(cart, "WheelLock") : null;
                    var ib = items ? Bounds(items.gameObject) : cart ? Bounds(cart) : new Bounds(Ground(at, 1f), Vector3.one);
                    var lockP = lk ? lk.position : ib.center - Vector3.up * 0.6f;
                    var top = new Vector3(ib.center.x, ib.max.y - 0.06f, ib.center.z);
                    var toLock = lockP - top; toLock.y = 0f;
                    top += toLock.normalized * Mathf.Min(0.35f, toLock.magnitude * 0.5f);
                    g = Group("Satchel", top, cart ? cart.transform.eulerAngles.y : facing, cart ? cart.transform : propsRoot);
                    var part = LevelPart("Satchel_cart");
                    if (part) { part.SetParent(g.transform, true); part.position = top + Vector3.up * 0.06f; part.rotation = g.transform.rotation * Quaternion.Euler(0, 15, 0); }
                    else Prim(PrimitiveType.Cube, "Bag", top + Vector3.up * 0.1f, new Vector3(0.32f, 0.22f, 0.12f), MatOr("M_Leather", "8A5A3A"), g.transform);
                    // 끈: 가방 → 바퀴 고정쇠
                    var a = top + Vector3.up * 0.04f; var b = lockP;
                    var strap = Prim(PrimitiveType.Cube, "Strap", (a + b) / 2f, new Vector3(0.035f, 0.012f, Vector3.Distance(a, b)), MatOr("M_Leather", "8A5A3A"), g.transform);
                    strap.transform.rotation = Quaternion.LookRotation(b - a);
                    foreach (var c in g.GetComponentsInChildren<Collider>()) Object.DestroyImmediate(c);
                    break;
                }
                case "cord_basket":
                    if (!HasModel("CordBasket"))
                    {
                        g = Model("Basket", Ground(at), facing, propsRoot, 1f, keepColliders: false);
                        Model("RedCord", g.transform.position + Vector3.up * 0.42f, facing, g.transform, 1f, keepColliders: false).name = "Cords";
                    }
                    break;
                case "chairs":
                {
                    g = Group("AlleyChairs", Ground(at));
                    if (alleyChairs.Count > 0) break;   // 2차 지형: 의자 + 천 덮은 덩어리는 BuildSlice2Dressing(alley_seated_lumps)
                    var alley = C("alley");
                    for (int i = 0; i < 6; i++)
                    {
                        var cp = Ground(alley + new Vector2(-9 + i * 3.4f, 3.8f));
                        var chair = Model("Chair", cp, 180, g.transform);
                        alleyChairs.Add(chair.transform);
                        var l = Model("Lump_" + (1 + i % 3), cp + Vector3.up * 0.5f, 180, chair.transform, 1f, keepColliders: false); l.name = "Lump";
                        Cover(l, cp + Vector3.up * 0.5f, 180);
                    }
                    break;
                }
                case "brother_lump":
                {
                    // 형 덩어리: kid_house_chair 의자 + Lump_Brother(목에 붉은 끈) + 천 덮개(Cover). 의자 다리 = 「형」 긁은 자리
                    var kcd = slice.TryGetValue("kid_house_chair", out var kc) ? kc as Dictionary<string, object> : null;
                    var cxz = kcd != null ? J.List(kcd, "chair") : null;
                    var cp = Ground(cxz != null && cxz.Count >= 2 ? new Vector2(J.F(cxz[0]), J.F(cxz[1])) : at);
                    float y = kcd != null ? J.F(kcd["yaw"]) : facing, sy = kcd != null && kcd.TryGetValue("seat_y", out var sv) ? J.F(sv) : 0.5f;
                    g = Group("BrotherLump", cp, y);
                    Model("Chair", cp, y, g.transform);
                    var lump = Model(J.Str(p.Raw, "model", "Lump_Brother"), cp + Vector3.up * sy, y, g.transform, 1f, keepColliders: false);
                    lump.name = "Lump";
                    Cover(lump, cp + Vector3.up * sy, y);
                    GlyphSpot(g.transform, new Vector3(0.27f, 0.22f, 0.27f), 0.16f);
                    break;
                }
                case "cord_hook":
                {
                    // 키노피오 집 앞벽(문 옆) 1.1 m 높이에 빈 고리 + 끊어진 붉은 끈
                    float y = hasFacing ? facing : KidHouseYaw();
                    var hp = new Vector3(at.x, Ground(ZoneXZ("z_kid_house", at)).y + 1.1f, at.y);   // 집 벽 위로 쏘면 지붕에 닿으므로 마당 높이 기준
                    if (HasModel("CordHook")) g = Model("CordHook", hp, y, propsRoot, 1f, keepColliders: false);
                    else { g = Model("Latch", hp, y, propsRoot, 1f, keepColliders: false); Model("RedCord", hp, y, g.transform, 0.8f, keepColliders: false); }
                    break;
                }
                case "kid_workbench":
                {
                    // 작업대(숫돌·톱밥·깎다 만 나무 새 다섯) — 집 앞쪽을 봄. 모델이 없으면 톱밥 + 숫돌
                    float y = hasFacing ? facing : KidHouseYaw();
                    bool bench = HasModel("KidWorkbench");
                    g = Model(bench ? "KidWorkbench" : "SawdustPile", Ground(at), y, propsRoot, 1f, keepColliders: false);
                    if (!bench) Model("NoseFileStone", g.transform.position + g.transform.right * 0.5f, y, g.transform, 0.8f, keepColliders: false);
                    break;
                }
                case "bark_door":
                {
                    // 골목→굴 틈 길을 막는 고목 껍질 문. 앞(+Z)이 골목(z_crack) 쪽, Door 피벗 = 경첩. 닫혀 있으면 길을 막음
                    var crack = ZoneXZ("z_crack", C("alley"));
                    float y = hasFacing ? facing : YawToward(at, crack);
                    g = Model(HasModel("BarkDoor") ? "BarkDoor" : "Sketch_Wall_1", Ground(at), y, propsRoot, 1f, keepColliders: false);
                    Blocker(g.transform, Ground(at), new Vector3(1.3f, 2.2f, 0.5f), y);
                    break;
                }
                case "wall_drawing":
                {
                    // 굴 벽 숯 그림: Level의 Face_hideout(UV 0~1 판)을 쓰고, 없으면 WallDrawing. 그림은 상태마다 PropState가 바꿈
                    var face = LevelPart("Face_hideout");
                    if (face) { g = Group("WallDrawing", face.position); face.SetParent(g.transform, true); }
                    else g = Model(J.Str(p.Raw, "model", "WallDrawing"), Ground(at), hasFacing ? facing : YawToward(at, C("hideout")), propsRoot, 1f, keepColliders: false);
                    ApplyPicture(g, "wall_drawing");
                    break;
                }
                case "lump_spat":
                {
                    // 물고기가 뱉은 덩어리(붉은 끈 맨 채)
                    g = Model(J.Str(p.Raw, "model", "Lump_4"), Ground(at), hasFacing ? facing : YawToward(at, C("field")), propsRoot, 1f, keepColliders: false);
                    Model("RedCord", FrontTop(g, 0.8f), g.transform.eulerAngles.y, g.transform, 1f, keepColliders: false);
                    break;
                }
                case "tracks":
                {
                    g = Group("Tracks", Ground(at));
                    var a = ZoneXZ("z_cart_procession", new Vector2(36, -5)); var b = ZoneXZ("z_pond_edge", new Vector2(54, -15));
                    var ink = MatOr("M_Ink", "2B2622");
                    for (int side = -1; side <= 1; side += 2)
                    {
                        var dir = (b - a).normalized; var nrm = new Vector2(-dir.y, dir.x) * 0.55f * side;
                        var q = Prim(PrimitiveType.Cube, "Track", Ground((a + b) / 2f + nrm, 0.02f), new Vector3(0.08f, 0.01f, (b - a).magnitude), ink, g.transform, new Vector3(0, YawToward(a, b), 0));
                        Object.DestroyImmediate(q.GetComponent<Collider>());
                    }
                    break;
                }
                case "sign": g = Model("Signpost", Ground(at), hasFacing ? facing : YawToward(at, C("field")) + 180, propsRoot); break;
                case "pond":
                {
                    g = Model("Pond", Ground(at, 0.02f), 0, propsRoot, 0.9f);
                    var surf = FindPart(g, "Surface");
                    if (surf) surf.gameObject.AddComponent<PondSurface>();
                    break;
                }
                case "pond_stone": g = Model("Rock_2", Ground(at), facing, propsRoot, 0.5f); break;   // 꾸밈 돌(새김 없음)
                case "door_nose":
                {
                    // 4-1 껍질 문 옹이 구멍으로 삐죽 나온 연필 코끝(문 앞 = 골목 쪽으로). long = Base + Piece, short = Piece가 떨어져 문 앞 땅에(Fallen)
                    var door = propObjects.TryGetValue("bark_door", out var dg) ? dg : null;
                    var knot = door ? FindPart(door, "Knot") : null;
                    var kp = knot ? knot.GetComponentInChildren<Renderer>()?.bounds.center ?? knot.position : Ground(at, 1.0f);
                    var fwd = door ? door.transform.forward : Vector3.forward;
                    g = Group("DoorNose", kp, door ? door.transform.eulerAngles.y : facing);
                    var pencil = MatOr("M_SketchNose", "B9B2A6"); var lead = MatOr("M_Pencil", "5A5650");
                    Material[] ms = { pencil, pencil, lead };
                    (string n, float from, float len, float r)[] segs = { ("Base", 0f, 0.14f, 0.022f), ("Piece", 0.14f, 0.24f, 0.016f), ("Tip", 0.38f, 0.05f, 0.008f) };
                    for (int i = 0; i < segs.Length; i++)
                    {
                        var sgo = Prim(PrimitiveType.Cylinder, segs[i].n, kp + fwd * (segs[i].from + segs[i].len * 0.5f), new Vector3(segs[i].r * 2f, segs[i].len * 0.5f, segs[i].r * 2f), ms[i], g.transform);
                        sgo.transform.up = fwd;   // 원기둥 길이(로컬 Y)가 문 앞쪽으로
                        Object.DestroyImmediate(sgo.GetComponent<Collider>());
                    }
                    FindPart(g, "Tip").SetParent(FindPart(g, "Piece"), true);   // 조각과 함께 떨어짐
                    // 떨어진 조각: 문 앞 땅에 누움
                    var fall = Prim(PrimitiveType.Cylinder, "Fallen", Ground(new Vector2(kp.x, kp.z) + new Vector2(fwd.x, fwd.z) * 0.35f, 0.02f), new Vector3(0.032f, 0.12f, 0.032f), pencil, g.transform, new Vector3(90, (door ? door.transform.eulerAngles.y : facing) + 35f, 0));
                    Object.DestroyImmediate(fall.GetComponent<Collider>());
                    break;
                }
                case "brother_knot2":
                {
                    // 형 덩어리 목 끈(Lump_Brother Cord, 피벗 = 매듭)의 둘째 고리 — 주인공 망토 끈 twice와 같은 꼴
                    var bl = propObjects.TryGetValue("brother_lump", out var bg2) ? bg2 : null;
                    var cord = bl ? FindPart(bl, "Cord") : null;
                    var kp = cord ? cord.position : Ground(at, 0.9f);
                    var rot = cord ? cord.rotation : Quaternion.Euler(0, facing, 0);
                    g = Group("BrotherKnot2", kp, 0f);
                    var loop = Model("RedCord", kp + rot * new Vector3(0.025f, -0.03f, 0.008f), 0f, g.transform, 0.85f, keepColliders: false);
                    loop.transform.rotation = rot * Quaternion.Euler(0, 0, 25f);
                    break;
                }
                case "kid_hand":
                case "wall_hero":
                    g = Group("Prop_" + p.Id, Ground(at));   // 보이지 않는 자리 / 다른 물건의 상태
                    break;
            }
            if (g == null)
            {
                var mn = NewModels.TryGetValue(p.Id, out var nm) && HasModel(nm.model) ? nm.model : J.Str(p.Raw, "model", null);
                float sc = nm.model != null && mn == nm.model ? nm.scale : p.Raw.TryGetValue("scale", out var so) ? J.F(so) : 1f;
                if (mn != null) g = Model(mn, Ground(at), facing, propsRoot, sc, keepColliders: false);
            }
            if (g == null) g = Group(p.Id, Ground(at));
            g.name = "Prop_" + p.Id;
            // 살펴보기 물건(inspect): 누르면 주인공 생각이 뜸(사건 touch:<id>)
            if (p.Raw.TryGetValue("inspect", out var label))
            {
                var lump = g.transform.Find("Lump");   // 형 덩어리: 덩어리(천)만 — 의자 다리는 「형」 글자 자리
                var lb = LocalBounds(lump ? lump.gameObject : g, g.transform);
                var box = g.AddComponent<BoxCollider>(); box.center = lb.center;
                box.size = Vector3.Max(lb.size, new Vector3(0.8f, 0.6f, 0.8f));
                var it = g.AddComponent<Interactable>(); it.kind = Interactable.Kind.Item; it.id = p.Id; it.approachDistance = 1.1f; it.hoverLabel = label.ToString();
            }
            if (!NavSolid.Contains(p.Id)) g.AddComponent<NavMeshModifier>().ignoreFromBuild = true;
            var ps = g.AddComponent<PropState>(); ps.propId = p.Id; ps.state = p.Initial;
            if (linked != null) ps.linked = linked.ToArray();
            return g;
        }

        /// <summary>길(구간들)을 따라 간격마다 하나씩, 좌우로 번갈아 비켜 놓음. 땅 높이가 튀면(지붕·무대 위) 건너뜀. light = 횃불 불꽃에 작은 등.</summary>
        static void PlaceAlong(Transform parent, IEnumerable<(Vector2 a, Vector2 b)> segs, float step, float side, string model, float scale, bool light)
        {
            int k = 0;
            foreach (var (a, b) in segs)
            {
                float len = Vector2.Distance(a, b); if (len < 0.5f) continue;
                var dir = (b - a) / len; var nrm = new Vector2(-dir.y, dir.x);
                float ya = Ground(a).y, yb = Ground(b).y;
                int n = Mathf.Max(1, Mathf.RoundToInt(len / step));
                for (int i = 0; i < n; i++, k++)
                {
                    float t = (i + 0.5f) / n;
                    var p = Vector2.Lerp(a, b, t) + nrm * side * (k % 2 == 0 ? 1f : -1f) * (light ? 1f : 0.4f + (float)rnd.NextDouble() * 0.6f);
                    var gp = Ground(p, 0.01f);
                    if (Mathf.Abs(gp.y - Mathf.Lerp(ya, yb, t)) > 0.6f) continue;
                    float yaw = light ? YawToward(p, Vector2.Lerp(a, b, t)) : (float)rnd.NextDouble() * 360f;
                    var m = Model(model, gp, yaw, parent, scale * (light ? 1f : 0.8f + (float)rnd.NextDouble() * 0.4f), keepColliders: false);
                    if (!light) continue;
                    var flame = FindPart(m, "Flame");
                    var l = PointLight(m.transform, Vector3.zero, "FFB060", 2.5f, 4.5f, "FlameLight");
                    l.transform.position = flame ? flame.position + Vector3.up * 0.15f : m.transform.position + Vector3.up * 2f;
                }
            }
        }

        static void Blocker(Transform parent, Vector3 pos, Vector3 size, float yaw)
        {
            var b = new GameObject("Blocker");
            b.transform.SetParent(parent, true);
            b.transform.position = pos; b.transform.rotation = Quaternion.Euler(0, yaw, 0);
            var ob = b.AddComponent<NavMeshObstacle>(); ob.carving = true; ob.carveOnlyStationary = false; ob.shape = NavMeshObstacleShape.Box; ob.size = size; ob.center = new Vector3(0, size.y / 2f, 0);
        }

        static void BuildProps()
        {
            // 그림판(board) 먼저 — 새 띠가 판3에 붙음. 수레 다음 가방(수레 위)
            // 문·형 덩어리 다음 코끝·둘째 고리(그 자리에 붙음)
            foreach (var p in data.Props.Values.OrderBy(p => p.Id == "board" ? 0 : p.Id == "cart" ? 1 : p.Id == "bark_door" || p.Id == "brother_lump" ? 2 : 3))
                propObjects[p.Id] = PropObject(p);
        }

        // ── 인물에 붙는 물건(props[].attach) ───────────────
        /// <summary>주인공·키노피오 뼈(Body·Head·HandR)에 붙임. 숨김은 PropState(attached)가 자식을 꺼서 함.</summary>
        static void AttachProps(GameObject player)
        {
            foreach (var p in data.Props.Values)
            {
                var who = J.Str(p.Raw, "attach", null);
                if (who == null || !propObjects.TryGetValue(p.Id, out var g)) continue;
                var body = who == "hero" ? player.transform : npcRoot.Find("NPC_" + who);
                if (!body) { Debug.LogWarning("[OUAT] 붙일 인물 없음: " + p.Id + " → " + who); continue; }
                var vis = body.Find("Visual") ? body.Find("Visual").gameObject : body.gameObject;
                var torso = FindPart(vis, "Body"); var head = FindPart(vis, "Head"); var hand = FindPart(vis, "HandR");
                float neckY = head ? head.position.y : body.position.y + 0.7f;
                float torsoY = torso ? torso.position.y : body.position.y + 0.45f;
                var ps = g.GetComponent<PropState>(); ps.attached = true;
                Transform bone = torso; Vector3 at;
                var model = J.Str(p.Raw, "model", null);
                switch (p.Id)
                {
                    case "hero_bag":
                    {
                        // 주인공 몸 메시에서 떼어 낸 Satchel을 켜고 끔
                        var sat = FindPart(vis, "Satchel");
                        at = sat ? Bounds(sat.gameObject).center : body.position + Vector3.up * torsoY;
                        if (sat) ps.linked = new[] { sat.gameObject };
                        else if (HasModel("Satchel")) model = "Satchel";
                        else Debug.LogWarning("[OUAT] 주인공 Satchel 메시 없음 — hero_bag taken이 안 보임");
                        break;
                    }
                    case "hero_spoon":
                        bone = hand ?? torso; at = hand ? hand.position : FrontPoint(vis, body, torsoY);
                        break;
                    case "kid_badge": at = FrontPoint(vis, body, Mathf.Lerp(torsoY, neckY, 0.55f)); break;
                    case "boss_bag":
                    {
                        // 우두머리가 두 손으로 받쳐 든 주인공 가방: 두 손 가운데(오른손 뼈를 따라감)
                        var handL = FindPart(vis, "HandL");
                        bone = hand ?? torso;
                        at = hand && handL ? (hand.position + handL.position) * 0.5f + Vector3.up * 0.08f : FrontPoint(vis, body, Mathf.Lerp(torsoY, neckY, 0.3f)) + body.forward * 0.15f;
                        break;
                    }
                    default: at = FrontPoint(vis, body, neckY - 0.04f); break;   // 붉은 끈: 망토 걸쇠 앞 / 키노피오 목
                }
                g.transform.SetParent(bone ? bone : body, true);
                g.transform.position = at; g.transform.rotation = body.rotation;
                float cordScale = who == "hero" ? 0.8f : 0.65f;
                switch (p.Id)
                {
                    case "hero_cord":
                    case "kid_cord":
                    {
                        Model(model ?? "RedCord", at, body.eulerAngles.y, g.transform, cordScale, keepColliders: false);
                        if (p.Id == "hero_cord")
                        {
                            // 두 번 감음: 둘째 고리(조금 아래·옆으로 비켜 기울임)
                            var loop2 = Model(model ?? "RedCord", at + body.right * 0.025f - Vector3.up * 0.03f + body.forward * 0.008f, body.eulerAngles.y, g.transform, cordScale * 0.9f, keepColliders: false);
                            loop2.transform.rotation = body.rotation * Quaternion.Euler(0, 0, 25f);
                            loop2.name = "Loop2";
                        }
                        break;
                    }
                    case "hero_spoon":
                    {
                        // 사람 숟가락(모델 없음): 놋쇠 자루 + 오목한 머리
                        var brass = MatOr("M_Brass", "C8902E");
                        var handle = Prim(PrimitiveType.Cylinder, "Handle", at, new Vector3(0.014f, 0.07f, 0.014f), brass, g.transform);
                        handle.transform.rotation = body.rotation * Quaternion.Euler(70, 0, 0);
                        Prim(PrimitiveType.Sphere, "Bowl", at + handle.transform.up * 0.08f, new Vector3(0.045f, 0.015f, 0.06f), brass, g.transform, handle.transform.eulerAngles);
                        break;
                    }
                    case "kid_badge":
                    {
                        // 파랑새 배지: 파란 반짝임(번짐) + 작은 파란 등
                        var glow = Unlit("M_BadgeGlow", new Color(0.45f, 0.75f, 2.4f, 1f));
                        Prim(PrimitiveType.Cylinder, "Badge", at, new Vector3(0.07f, 0.006f, 0.07f), glow, g.transform, (body.rotation * Quaternion.Euler(90, 0, 0)).eulerAngles);
                        PointLight(g.transform, Vector3.zero, "4A86FF", 1.4f, 1.6f, "Glint").transform.position = at + body.forward * 0.12f;
                        break;
                    }
                    case "boss_bag":
                    {
                        // 주인공 Satchel 메시를 그대로 본뜬 사본(가운데를 손 사이에)
                        var sat = FindPart(player.transform.Find("Visual") ? player.transform.Find("Visual").gameObject : player, "Satchel");
                        var smr = sat ? sat.GetComponent<SkinnedMeshRenderer>() : null;
                        var mesh = smr ? smr.sharedMesh : sat && sat.GetComponent<MeshFilter>() ? sat.GetComponent<MeshFilter>().sharedMesh : null;
                        if (mesh)
                        {
                            var copy = new GameObject("Satchel");
                            copy.transform.SetParent(g.transform, false);
                            copy.transform.localRotation = Quaternion.Inverse(player.transform.rotation) * sat.rotation;
                            copy.transform.localScale = sat.lossyScale;
                            copy.transform.localPosition = -(copy.transform.localRotation * Vector3.Scale(mesh.bounds.center, sat.lossyScale));
                            copy.AddComponent<MeshFilter>().sharedMesh = mesh;
                            copy.AddComponent<MeshRenderer>().sharedMaterials = sat.GetComponent<Renderer>().sharedMaterials;
                        }
                        else Prim(PrimitiveType.Cube, "Satchel", at, new Vector3(0.3f, 0.22f, 0.1f), MatOr("M_Leather", "8A5A3A"), g.transform, body.eulerAngles);
                        break;
                    }
                    default:
                        if (model != null) Model(model, at, body.eulerAngles.y, g.transform, 1f, keepColliders: false);
                        break;
                }
                foreach (var c in g.GetComponentsInChildren<Collider>(true)) Object.DestroyImmediate(c);
                foreach (var r in g.GetComponentsInChildren<Renderer>(true)) r.shadowCastingMode = ShadowCastingMode.Off;
                var mod = g.GetComponent<NavMeshModifier>(); if (mod) Object.DestroyImmediate(mod);
            }
        }

        /// <summary>인물 몸 앞면 위의 점(그 높이에서 가운데 줄 정점 중 가장 앞). 메시를 못 읽으면 몸 앞 0.12 m.</summary>
        static Vector3 FrontPoint(GameObject vis, Transform body, float y)
        {
            var fwd = body.forward; var right = body.right; var o = body.position;
            float best = float.MinValue;
            foreach (var r in vis.GetComponentsInChildren<Renderer>(true))
            {
                if (r.name.StartsWith("Satchel") || r.name.StartsWith("Mark")) continue;
                Mesh m = r is SkinnedMeshRenderer sk ? sk.sharedMesh : r.GetComponent<MeshFilter>()?.sharedMesh;
                if (!m || !m.isReadable) continue;
                var mtx = r.transform.localToWorldMatrix;
                foreach (var v in m.vertices)
                {
                    var w = mtx.MultiplyPoint3x4(v);
                    if (Mathf.Abs(w.y - y) > 0.04f || Mathf.Abs(Vector3.Dot(w - o, right)) > 0.07f) continue;
                    best = Mathf.Max(best, Vector3.Dot(w - o, fwd));
                }
            }
            if (best == float.MinValue) best = 0.12f;
            var p = o + fwd * (best + 0.01f); p.y = y;
            return p;
        }

        // ── 그림판·새김 ───────────────────────────────────
        /// <summary>slice2 picture_boards 자리마다 그림판. 같은 자리(0.8 m 안)에 host 없는 새김이 있으면 그 판이 그 새김(ins_board_whale·ins_board_chair), 나머지는 빈 틀.</summary>
        static void BuildPictureBoards(Transform root)
        {
            foreach (var o in J.List(slice, "picture_boards").OfType<Dictionary<string, object>>())
            {
                var pp = J.List(o, "pos"); if (pp.Count < 2) continue;
                var pos = new Vector2(J.F(pp[0]), J.F(pp[1]));
                var board = Model("PictureBoard", Ground(pos), o.TryGetValue("yaw", out var y) ? J.F(y) : YawToward(pos, C("plaza")), root);
                board.name = "Board_" + J.Str(o, "id");
                var ins = data.Inscriptions.Values.FirstOrDefault(i => J.Str(i.Raw, "host", null) == null && Vector2.Distance(i.Pos, pos) < 0.8f);
                if (ins != null) boardForIns[ins.Id] = board;
            }
        }

        static Transform GlyphSpot(Transform parent, Vector3 local, float width)
        {
            var s = new GameObject("GlyphSpot").transform;
            s.SetParent(parent, false); s.localPosition = local; s.localRotation = Quaternion.identity;
            s.localScale = new Vector3(width, 1f, 1f);   // 글자 줄 너비(m)를 x에 담음
            return s;
        }

        static Transform NearestChair(Vector2 p, float within)
        {
            Transform best = null; float bd = within;
            foreach (var c in alleyChairs) { float d = Vector2.Distance(new Vector2(c.position.x, c.position.z), p); if (d < bd) { bd = d; best = c; } }
            return best;
        }

        static void BuildInscriptions()
        {
            var boardsRoot = propObjects.TryGetValue("board", out var bg) ? bg.transform : propsRoot;
            foreach (var ins in data.Inscriptions.Values)
            {
                var hostId = J.Str(ins.Raw, "host", null);
                var image = J.Str(ins.Raw, "image", null);
                var targets = new List<(GameObject host, Transform spot)>();
                if (hostId != null && propObjects.TryGetValue(hostId, out var hp))
                {
                    // copies: 같은 글이 여러 자리(골목 의자 등받이마다)
                    foreach (var c in J.List(ins.Raw, "copies").OfType<List<object>>())
                    {
                        var chair = c.Count >= 2 ? NearestChair(new Vector2(J.F(c[0]), J.F(c[1])), 2f) : null;
                        if (chair && !targets.Any(t => t.host == chair.gameObject)) targets.Add((chair.gameObject, GlyphSpot(chair, new Vector3(0, 1.32f, -0.30f), 0.5f)));
                    }
                    if (targets.Count == 0) targets.Add((hp, hp.transform.Find("GlyphSpot")));
                }
                else if (hostId != null) Debug.LogWarning("[OUAT] 새김 host 물건 없음: " + ins.Id + " → " + hostId);
                bool pictureBoard = false;
                if (targets.Count == 0)
                {
                    GameObject host;
                    if (boardForIns.TryGetValue(ins.Id, out var bd)) host = bd;
                    else if (ins.IsDisplay || image != null) host = Model("PictureBoard", Ground(ins.Pos), YawToward(ins.Pos, C("plaza")), boardsRoot);
                    else if (ins.Place == "hideout") host = Model("WallDrawing", Ground(ins.Pos), YawToward(ins.Pos, C("hideout")), propsRoot, 1f, keepColliders: false);   // 굴 벽 새김
                    else host = Model("StoneTablet", Ground(ins.Pos), YawToward(ins.Pos, C(string.IsNullOrEmpty(ins.Place) ? "plaza" : ins.Place)) + 180, propsRoot);
                    pictureBoard = ins.IsDisplay && hostId == null;
                    targets.Add((host, null));
                }
                foreach (var (host, spot) in targets)
                {
                    if (pictureBoard) ApplyPicture(host, image ?? ins.Id);   // 그림판(표시 글): 그림만, 글자는 화면에서
                    else if (image != null && !spot) { ApplyPicture(host, image); PlaceGlyphs(host, ins.Lines, null, band: true); }   // 그림 + 그 밑 글자 줄
                    else PlaceGlyphs(host, ins.Lines, spot);
                    var trigger = new GameObject("Inscription_" + ins.Id);
                    trigger.transform.SetParent(spot ? spot.parent : host.transform, false);
                    var box = trigger.AddComponent<BoxCollider>();
                    Vector3 top;
                    if (spot)
                    {
                        trigger.transform.localPosition = spot.localPosition; trigger.transform.localRotation = spot.localRotation;
                        box.size = new Vector3(spot.localScale.x + 0.3f, Mathf.Max(0.45f, spot.localScale.x), 0.4f);
                        top = spot.position + Vector3.up * 0.4f;
                    }
                    else
                    {
                        var lb = LocalBounds(host, host.transform);
                        box.center = lb.center; box.size = Vector3.Max(lb.size, new Vector3(1.0f, 1.0f, 0.5f));
                        top = host.transform.TransformPoint(new Vector3(lb.center.x, lb.max.y + 0.4f, lb.center.z));
                    }
                    trigger.AddComponent<NavMeshModifier>().ignoreFromBuild = true;
                    var it = trigger.AddComponent<Interactable>(); it.kind = Interactable.Kind.Inscription; it.id = ins.Id; it.approachDistance = 1.9f;
                    var mk = trigger.AddComponent<InscriptionMarker>(); mk.inscriptionId = ins.Id; mk.sentenceId = ins.Lines.FirstOrDefault();
                    var anchor = new GameObject("LabelAnchor").transform; anchor.SetParent(trigger.transform, false); anchor.position = top; mk.labelAnchor = anchor;
                }
            }
        }

        static void ApplyPicture(GameObject host, string id, float alpha = 1f, string part = "Face")
        {
            var tex = AssetDatabase.LoadAssetAtPath<Texture2D>($"Assets/Game/Resources/Pictures/{id}.png");
            var face = FindPart(host, part);
            if (!tex || !face) return;
            var r = face.GetComponent<Renderer>(); if (!r) return;
            var m = Unlit("Pic_" + id, new Color(1, 1, 1, alpha), alpha < 1f ? "alpha" : "opaque");
            m.SetTexture("_BaseMap", tex);
            r.sharedMaterial = m;
        }

        /// <summary>
        /// 크리처 글자를 줄마다 깐다(Glyphs/carved). spot이 있으면 그 자리(의자 등받이·다리, 너비 = spot 배율 x),
        /// 없으면 앞면(Face)이나 몸통 앞쪽. band = 그림판 그림 밑 글자 띠(앞면 아래쪽에 종이 띠 + 글자).
        /// </summary>
        static void PlaceGlyphs(GameObject host, List<string> lines, Transform spot = null, bool band = false)
        {
            Vector3 center, fwd, right; float width, height;
            if (spot)
            {
                center = spot.position; fwd = spot.forward; right = spot.right;
                width = spot.localScale.x; height = width * Mathf.Max(1, lines.Count);
            }
            else
            {
                var face = FindPart(host, "Face");
                var b = face && face.GetComponent<Renderer>() ? face.GetComponent<Renderer>().bounds : Bounds(host);
                fwd = host.transform.forward; right = host.transform.right;
                center = face ? b.center + fwd * 0.012f : b.center + fwd * (Vector3.Scale(b.extents, new Vector3(Mathf.Abs(fwd.x), 0, Mathf.Abs(fwd.z))).magnitude + 0.03f);
                width = Mathf.Max(0.9f, Vector3.Scale(b.size, new Vector3(Mathf.Abs(right.x), 0, Mathf.Abs(right.z))).magnitude);
                height = Mathf.Max(0.5f, b.size.y);
                if (band)
                {
                    height *= Mathf.Min(0.45f, 0.14f + 0.13f * Mathf.Max(1, lines.Count));   // 한 줄 27%, 두 줄 40%
                    center.y = b.min.y + height * 0.5f + 0.03f;
                    var strip = GameObject.CreatePrimitive(PrimitiveType.Quad); Object.DestroyImmediate(strip.GetComponent<Collider>());
                    strip.name = "GlyphBand"; strip.transform.SetParent(host.transform, true);
                    strip.transform.position = center - fwd * 0.004f; strip.transform.rotation = Quaternion.LookRotation(-fwd, Vector3.up);
                    var ls = new Vector3(width * 0.94f, height, 1f); var hs = host.transform.lossyScale;
                    strip.transform.localScale = new Vector3(ls.x / Mathf.Max(0.0001f, hs.x), ls.y / Mathf.Max(0.0001f, hs.y), 1f);
                    var sr = strip.GetComponent<Renderer>(); sr.sharedMaterial = Unlit("M_GlyphBand", Hex("EDE6D6")); sr.shadowCastingMode = ShadowCastingMode.Off;
                    center += fwd * 0.004f;
                }
            }
            int rows = Mathf.Max(1, lines.Count);
            float rowH = Mathf.Min(height * 0.85f / rows, 0.42f);
            for (int li = 0; li < lines.Count; li++)
            {
                if (!data.Sentences.TryGetValue(lines[li] ?? "", out var spec)) continue;
                var words = Flatten(spec).ToList();
                float w = Mathf.Min(rowH, width * 0.9f / Mathf.Max(1, words.Count));
                float y = (rows - 1) * rowH * 0.5f - li * rowH;
                for (int i = 0; i < words.Count; i++)
                {
                    var tex = AssetDatabase.LoadAssetAtPath<Texture2D>($"Assets/Game/Resources/Glyphs/carved/{words[i]}.png") ?? AssetDatabase.LoadAssetAtPath<Texture2D>($"Assets/Game/Resources/Glyphs/{words[i]}.png");
                    if (!tex) continue;
                    var q = GameObject.CreatePrimitive(PrimitiveType.Quad); Object.DestroyImmediate(q.GetComponent<Collider>());
                    q.name = "Glyph_" + words[i];
                    q.transform.SetParent(host.transform, true);
                    q.transform.position = center + right * (-(words.Count - 1) * w * 0.5f + i * w) + Vector3.up * y;
                    q.transform.rotation = Quaternion.LookRotation(-fwd, Vector3.up);
                    q.transform.localScale = Vector3.one * w / Mathf.Max(0.0001f, host.transform.lossyScale.x);
                    var m = Unlit("Glyph_" + words[i], Color.white, "alpha");
                    m.SetTexture("_BaseMap", tex);
                    var rr = q.GetComponent<Renderer>(); rr.sharedMaterial = m; rr.shadowCastingMode = ShadowCastingMode.Off;
                }
            }
        }

        static IEnumerable<string> Flatten(Jigsaw.SpecNode n)
        {
            if (n == null) yield break;
            if (!string.IsNullOrEmpty(n.Word)) yield return n.Word;
            foreach (var c in n.Children) foreach (var w in Flatten(c)) yield return w;
        }

        static void BuildReadables()
        {
            foreach (var rd in data.Readables.Values)
            {
                if (rd.Raw != null && rd.Raw.ContainsKey("attached")) continue;   // 다른 물건을 누르면 열리는 글(떨어진 책 등)
                var host = Model("PinocchioPage", Ground(rd.Pos, 0.02f), rd.Raw != null && rd.Raw.TryGetValue("facing", out var rf) ? J.F(rf) : 0f, propsRoot);
                host.name = "Readable_" + rd.Id;
                ApplyPicture(host, rd.Id);
                var b = Bounds(host);
                var box = host.AddComponent<BoxCollider>(); box.center = host.transform.InverseTransformPoint(b.center); box.size = new Vector3(1.2f, 0.6f, 1.2f);
                var it = host.AddComponent<Interactable>(); it.kind = Interactable.Kind.Item; it.id = rd.Id; it.approachDistance = 1.2f; it.hoverLabel = rd.Label;
                host.AddComponent<NavMeshModifier>().ignoreFromBuild = true;
                // visibleWhen(all) 전에는 낱장도 안 보이게(누르기만 막으면 땅에 보이는 채로 남음)
                if (rd.Raw != null && rd.Raw.TryGetValue("visibleWhen", out var vw) && vw is Dictionary<string, object> vwd && J.Strings(vwd, "all").Count > 0)
                {
                    var ps = host.AddComponent<PropState>(); ps.propId = rd.Id; ps.state = "default"; ps.visibleAll = J.Strings(vwd, "all").ToArray();
                }
            }
        }

        // ── 장치 퍼즐 ─────────────────────────────────────
        /// <summary>puzzles[].host 물건에 PuzzleObject, 누르는 자리 Use_&lt;id&gt;(zone이 있으면 그 자리 — 움직이는 부품이 1.5 m 안이면 부품), 글 = puzzles[].label.</summary>
        static void BuildPuzzles()
        {
            foreach (var pz in data.Puzzles.Values)
            {
                var hostId = J.Str(pz.Raw, "host", null);
                if (hostId == null || !propObjects.TryGetValue(hostId, out var host)) continue;   // pick(짚기)는 Game이 맡음
                var po = host.AddComponent<PuzzleObject>(); po.puzzleId = pz.Id;
                po.movingPart = FindPart(host, "Latch") ?? FindPart(host, "WheelLock") ?? FindPart(host, "Lid") ?? FindPart(host, "Rope");
                if (po.movingPart && po.movingPart.name.StartsWith("Lid")) { po.openedLocalEuler = new Vector3(-100, 0, 0); po.openedLocalOffset = Vector3.zero; }   // 오르골 뚜껑
                if (pz.Type == "drawnBolt" || pz.Type == "pick") continue;
                var target = po.movingPart ? po.movingPart.position : Bounds(host).center;
                var zoneId = J.Str(pz.Raw, "zone", null);
                if (zoneId != null && data.Zones.TryGetValue(zoneId, out var z))
                {
                    var zp = Ground(z.Pos, 0.5f);
                    if (!po.movingPart || Vector2.Distance(new Vector2(target.x, target.z), z.Pos) > 1.5f) target = zp;
                }
                var trigger = new GameObject("Use_" + pz.Id);
                trigger.transform.SetParent(host.transform, true);
                trigger.transform.position = target;
                trigger.AddComponent<BoxCollider>().size = new Vector3(1.1f, 1.1f, 1.1f);
                trigger.AddComponent<NavMeshModifier>().ignoreFromBuild = true;
                var it = trigger.AddComponent<Interactable>(); it.kind = Interactable.Kind.Puzzle; it.id = pz.Id; it.approachDistance = 1.1f;
                it.hoverLabel = J.Str(pz.Raw, "label", pz.Type == "untie" ? "사람 끈 풀기" : "사람 걸쇠 풀기");
                it.available = false;
            }
        }

        static FishActor BuildFish()
        {
            var at = data.Props.TryGetValue("pond", out var pd) ? pd.Pos : C("pond");
            var root = new GameObject("Fish");
            root.transform.position = Ground(at);
            var model = Model("Fish", root.transform.position, 200, root.transform, 1f, keepColliders: false);
            model.transform.localPosition = Vector3.zero;
            var fa = root.AddComponent<FishActor>(); fa.model = model.transform;
            if (propObjects.TryGetValue("cart", out var cart)) fa.cartItemsRoot = FindPart(cart, "Items");
            return fa;
        }

        // ── 구역(장소·카메라) ─────────────────────────────
        static void BuildZones()
        {
            var views = new Dictionary<string, FollowCamera.View>
            {
                { "fall",  new FollowCamera.View { yaw = 30, pitch = 40, distance = 15, fov = 32, offset = new Vector3(0, 0.6f, 0) } },
                { "gate",  new FollowCamera.View { yaw = 40, pitch = 36, distance = 15, fov = 32, offset = new Vector3(0, 0.6f, 0) } },
                { "plaza", new FollowCamera.View { yaw = 15, pitch = 32, distance = 19, fov = 34, offset = new Vector3(0, 1.2f, 2) } },
                { "alley", new FollowCamera.View { yaw = 50, pitch = 42, distance = 14, fov = 32, offset = new Vector3(0, 0.6f, 0) } },
                { "field", new FollowCamera.View { yaw = 35, pitch = 44, distance = 18, fov = 34, offset = new Vector3(0, 0.6f, 0) } },
                { "pond",  new FollowCamera.View { yaw = 25, pitch = 34, distance = 18, fov = 34, offset = new Vector3(0, 0.8f, 0) } },
            };
            foreach (var kv in Places)
            {
                var g = new GameObject("Place_" + kv.Key);
                g.transform.SetParent(zoneRoot);
                var c = kv.Value.c;
                g.transform.position = Ground(c) + Vector3.up;
                var col = g.AddComponent<SphereCollider>(); col.isTrigger = true; col.radius = kv.Value.r;
                g.AddComponent<PlaceZone>().placeId = kv.Key;
                if (data.Areas.Count > 0) continue;   // 구역(areas[].camera)이 카메라를 정함 — 장소별 카메라가 덮어쓰지 않게
                var cz = g.AddComponent<CameraZone>(); cz.view = views.TryGetValue(kv.Key, out var v) ? v : FollowCamera.View.Default; cz.priority = 1;
            }
        }

        /// <summary>폭 1.2m 미만의 좁은 틈(골목→굴 등)은 바닥 모형이 몸통(반지름 0.3)보다 좁아 굽기에서 사라짐 —
        /// 굽는 동안만 쓰는 1.2m 폭 바닥 띠를 깔고, 굽고 나면 지움. 높이는 Ground_Walk 바닥에 맞춤(문·물건 위로 올라타지 않게).</summary>
        static List<GameObject> NarrowPassageStrips()
        {
            var made = new List<GameObject>();
            foreach (var a in data.Areas.Values)
                foreach (var sh in a.Shapes)
                {
                    if (sh.Line == null || sh.W >= 1.2f) continue;
                    for (int i = 0; i + 1 < sh.Line.Count; i++)
                    {
                        var p0 = WalkGround(sh.Line[i]); var p1 = WalkGround(sh.Line[i + 1]);
                        var d = p1 - p0; float len = d.magnitude; if (len < 0.05f) continue;
                        var g = new GameObject($"NavStrip_{a.Id}_{i}");
                        g.transform.position = (p0 + p1) / 2f + Vector3.down * 0.05f;
                        g.transform.rotation = Quaternion.LookRotation(d.normalized, Vector3.up);
                        var bc = g.AddComponent<BoxCollider>(); bc.size = new Vector3(1.2f, 0.1f, len + 0.5f);
                        made.Add(g);
                    }
                }
            Physics.SyncTransforms();
            return made;
        }

        static Vector3 WalkGround(Vector2 xz)
        {
            var hits = Physics.RaycastAll(new Vector3(xz.x, 50, xz.y), Vector3.down, 100f, ~0, QueryTriggerInteraction.Ignore);
            foreach (var h in hits.OrderBy(h => h.distance))
            {
                var t = h.collider.transform; bool walk = false;
                for (; t; t = t.parent) if (t.name.StartsWith("Ground_Walk")) { walk = true; break; }
                if (walk) return h.point;
            }
            return Ground(xz);
        }

        static void BakeNavMesh()
        {
            Physics.SyncTransforms();
            var surfaceGo = new GameObject("NavMesh");
            var s = surfaceGo.AddComponent<NavMeshSurface>();
            s.collectObjects = CollectObjects.All;
            s.useGeometry = NavMeshCollectGeometry.PhysicsColliders;
            s.layerMask = ~0;
            s.BuildNavMesh();
            var path = "Assets/Game/Scenes/Chapter1_NavMesh.asset";
            ProjectSetup.EnsureFolder("Assets/Game/Scenes");
            if (s.navMeshData)
            {
                AssetDatabase.DeleteAsset(path);
                AssetDatabase.CreateAsset(s.navMeshData, path);
            }
        }

        /// <summary>구운 길 찾기 영역이 실제로 이어지는지: 구역 안(가운데 → 출구)과 출구 → 건너편 도착 자리. 장애물(문·빗장)은 빼고 지형만 봄. 결과는 [OUAT] NAV 줄로.</summary>
        static void NavReport()
        {
            int bad = 0;
            bool Sample(Vector2 xz, out Vector3 p)
            {
                p = Vector3.zero;
                if (NavMesh.SamplePosition(Ground(xz), out var h, 2.5f, NavMesh.AllAreas)) { p = h.position; return true; }
                return false;
            }
            foreach (var a in data.Areas.Values)
            {
                var c = a.Shapes.Count > 0 ? (a.Shapes[0].Line != null ? a.Shapes[0].Line[0] : a.Shapes[0].C) : Vector2.zero;
                bool hasC = Sample(c, out var pc);
                foreach (var e in a.Exits)
                {
                    string msg;
                    if (!Sample(e.Pos, out var pe)) msg = "출구 자리에 길 없음";
                    else if (!Sample(e.Spawn, out var ps)) msg = "도착 자리에 길 없음";
                    else
                    {
                        // 구역끼리는 책장 넘김(순간 이동)이라 잇지 않음 — 이 구역 안(가운데→출구)과 건너편 구역 안(도착 자리→그 구역 가운데)만 봄
                        var inner = new NavMeshPath();
                        bool innerOk = !hasC || (NavMesh.CalculatePath(pc, pe, NavMesh.AllAreas, inner) && inner.status == NavMeshPathStatus.PathComplete);
                        bool farOk = true;
                        if (data.Areas.TryGetValue(e.To, out var ta) && ta.Shapes.Count > 0)
                        {
                            var tc = ta.Shapes[0].Line != null ? ta.Shapes[0].Line[0] : ta.Shapes[0].C;
                            if (Sample(tc, out var ptc)) { var far = new NavMeshPath(); farOk = NavMesh.CalculatePath(ps, ptc, NavMesh.AllAreas, far) && far.status == NavMeshPathStatus.PathComplete; }
                        }
                        msg = !innerOk ? "이 구역 가운데에서 출구까지 끊김" : !farOk ? "건너편 도착 자리에서 그 구역 가운데까지 끊김" : null;
                    }
                    if (msg != null)
                    {
                        bad++; Debug.LogWarning($"[OUAT] NAV {a.Id}→{e.To}: {msg}");
                        // 어디서 끊기나: 이 구역 가운데→출구 경로의 끝(갈 수 있는 마지막 점)과 그 둘레 충돌체
                        if (hasC && Sample(e.Pos, out var pe2))
                        {
                            var pp = new NavMeshPath(); NavMesh.CalculatePath(pc, pe2, NavMesh.AllAreas, pp);
                            var end = pp.corners.Length > 0 ? pp.corners[pp.corners.Length - 1] : pc;
                            var names = Physics.OverlapSphere(end, 1.6f).Select(cl => cl.transform.parent ? cl.transform.parent.name + "/" + cl.name : cl.name).Distinct().Take(8);
                            Debug.LogWarning($"[OUAT] NAV   끊긴 끝 {end} → 출구 {pe2} (남은 {Vector3.Distance(end, pe2):0.0}m) 둘레: {string.Join(", ", names)}");
                        }
                    }
                }
            }
            Debug.Log($"[OUAT] NAV 검사 끝 — 문제 {bad}개");
        }

        // ── 주인공 ───────────────────────────────────────
        static GameObject BuildPlayer()
        {
            var start = data.Zones.TryGetValue("z_hero_start", out var z) ? z.Pos : C("fall") + new Vector2(-3, 3);
            var root = new GameObject("Player");
            root.transform.position = Ground(start);
            var model = Model("Hero_Bluebird", root.transform.position, 0, root.transform, 1f, keepColliders: false);
            model.name = "Visual";
            model.transform.localPosition = Vector3.zero;
            var rig = root.AddComponent<ProceduralRig>(); rig.bobScale = 1.1f;   // 주인공은 사람 아이(파랑새 색), 클립이 있으면 클립으로
            var agent = root.AddComponent<NavMeshAgent>(); agent.baseOffset = 0;
            var col = root.AddComponent<CapsuleCollider>(); col.height = 1.1f; col.radius = 0.3f; col.center = new Vector3(0, 0.55f, 0);
            var rb = root.AddComponent<Rigidbody>(); rb.isKinematic = true;
            var mover = root.AddComponent<PlayerMover>();
            mover.walkSpeed = 1.8f; mover.runSpeed = Mathf.Max(3.2f, GameTuning.Get().walkSpeed);   // 사람 아이: 가까우면 걷고 멀면 뜀
            var markerGo = new GameObject("ClickMarker");
            var ring = Prim(PrimitiveType.Cylinder, "Ring", Vector3.zero, new Vector3(0.9f, 0.01f, 0.9f), Unlit("M_ClickRing", new Color(0.17f, 0.15f, 0.13f, 0.55f), "alpha"), markerGo.transform);
            Object.DestroyImmediate(ring.GetComponent<Collider>());
            mover.marker = markerGo.AddComponent<ClickMarker>();
            return root;
        }

        // ── 크리처 ───────────────────────────────────────
        static string ModelName(NpcDef n, int index)
        {
            var m = string.IsNullOrEmpty(n.Model) ? "Villager" : n.Model;
            if (m == "Villager") return "Villager_" + "ABC"[(Mathf.Abs(n.Id.GetHashCode()) + index) % 3];
            if (m == "Silhouette") return "Silhouette_" + "AB"[index % 2];
            return m;
        }

        // 데이터에 scale이 없을 때의 크기: 지킴이 = 아이 크기 실루엣, 밭 꼬마는 작게, 죽 주는 이는 배 불룩
        static readonly Dictionary<string, Vector3> NpcScale = new Dictionary<string, Vector3>
        {
            { "watcher", Vector3.one * 0.62f }, { "field_kid", Vector3.one * 0.68f }, { "porridge", new Vector3(1.18f, 1f, 1.25f) },
        };

        static Vector3 ScaleOf(NpcDef n)
        {
            if (n.Raw.TryGetValue("scale", out var s))
            {
                if (s is List<object> l && l.Count >= 3) return new Vector3(J.F(l[0]), J.F(l[1]), J.F(l[2]));
                if (J.F(s) > 0f) return Vector3.one * J.F(s);
            }
            return NpcScale.TryGetValue(n.Id, out var v) ? v : Vector3.one;
        }

        /// <summary>걷지 않는 크리처(데이터 "stationary": true, 또는 slice3의 창 안 이웃).</summary>
        static bool Stationary(NpcDef n) => J.Bool(n.Raw, "stationary", n.Id == "neighbor");

        static void BuildNpcs()
        {
            Physics.SyncTransforms();
            foreach (var n in data.Npcs.Values)
            {
                if (n.Id == "fish" || J.Str(n.Raw, "look", "") == "hidden") continue;
                var spawnL = J.List(n.Raw, "spawn");
                var spawn = spawnL.Count >= 2 ? new Vector2(J.F(spawnL[0]), J.F(spawnL[1])) : C(string.IsNullOrEmpty(n.Home) ? "gate" : n.Home);
                int count = n.Raw.TryGetValue("count", out var co) ? Mathf.Max(1, (int)J.F(co)) : 1;
                float facing = n.Raw.TryGetValue("facing", out var fo) ? J.F(fo) : 0f;
                for (int i = 0; i < count; i++)
                {
                    var p = spawn + (i == 0 ? Vector2.zero : new Vector2(Mathf.Cos(i * 2.1f), Mathf.Sin(i * 2.1f)) * (1.4f + i * 0.4f));
                    var id = i == 0 ? n.Id : n.Id + "_" + (i + 1);
                    MakeNpc(n, id, ModelName(n, i), Ground(p), facing + i * 23f);
                }
            }
        }

        /// <summary>크리처 하나: 모델(Visual) + ProceduralRig + NavMeshAgent + NpcActor + 머리 자리 + 누름(Npc — 줄 선 주민도 짚기 대상).</summary>
        static void MakeNpc(NpcDef n, string id, string modelName, Vector3 pos, float facing)
        {
            var root = new GameObject("NPC_" + id);
            root.transform.SetParent(npcRoot);
            root.transform.position = pos; root.transform.rotation = Quaternion.Euler(0, facing, 0);
            var model = Model(modelName, pos, facing, root.transform, 1f, keepColliders: false);
            model.name = "Visual";
            model.transform.localPosition = Vector3.zero; model.transform.localRotation = Quaternion.identity;
            var scale = ScaleOf(n);
            model.transform.localScale = Vector3.Scale(model.transform.localScale, scale);
            if (id == "kinopio") { var mark = FindPart(model, "Mark"); if (mark) mark.gameObject.SetActive(false); }
            bool small = scale.y < 0.8f;
            if (n.Id == "watcher")
            {
                // 지킴이: 막대기를 든 아이 크기 실루엣
                var hand = FindPart(model, "HandR");
                var at = hand ? hand.position : pos + root.transform.right * 0.2f + Vector3.up * 0.5f;
                var stick = Prim(PrimitiveType.Cylinder, "Stick", at + Vector3.down * 0.15f, new Vector3(0.03f, 0.5f * scale.y, 0.03f), MatOr("M_Wood", "E8C99A"), root.transform, new Vector3(0, facing, 8f));
                Object.DestroyImmediate(stick.GetComponent<Collider>());
                if (hand) stick.transform.SetParent(hand, true);   // 손을 따라감(뼈 배율과 무관하게 세계 크기 유지)
            }
            var rig = root.AddComponent<ProceduralRig>();
            if (Stationary(n))
            {
                // 창 안 등 걷는 땅 밖: 에이전트 없이 제자리(NpcActor는 에이전트가 없으면 Warp = 자리 옮기기). 집 지붕에 얹히지 않게 그 장소 땅 높이로
                root.transform.position = new Vector3(pos.x, Mathf.Min(pos.y, Ground(C(string.IsNullOrEmpty(n.Home) ? "alley" : n.Home)).y), pos.z);
            }
            else
            {
                var agent = root.AddComponent<NavMeshAgent>();
                agent.radius = id == "chief" ? 0.8f : small ? 0.28f : 0.35f; agent.height = id == "chief" ? 3.2f : small ? 1.0f : 1.4f;
                agent.avoidancePriority = id == "kinopio" ? 30 : 60;
            }
            var actor = root.AddComponent<NpcActor>(); actor.npcId = id;
            var b = Bounds(root);
            var col = root.AddComponent<CapsuleCollider>(); col.height = Mathf.Max(small ? 0.7f : 1f, b.size.y); col.radius = Mathf.Clamp(Mathf.Min(b.extents.x, b.extents.z), small ? 0.25f : 0.35f, 1.2f); col.center = new Vector3(0, col.height / 2f, 0);
            var head = new GameObject("HeadAnchor").transform; head.SetParent(root.transform, false); head.localPosition = new Vector3(0, b.size.y + 0.3f, 0);
            actor.headAnchor = head;
            var it = root.AddComponent<Interactable>(); it.kind = Interactable.Kind.Npc; it.id = id; it.approachDistance = id == "chief" ? 2.4f : 1.5f;
            it.available = true;
            if (n.Id == "watcher") root.SetActive(false);   // 대화3 「나→가다→안」 뒤에만 나옴(사건 npc show)
        }

        // ── 시스템 ───────────────────────────────────────
        static void BuildSystems(GameObject player, FishActor fish)
        {
            var tune = GameTuning.Get();
            var camGo = new GameObject("Main Camera") { tag = "MainCamera" };
            var cam = camGo.AddComponent<Camera>();
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = Hex("F1EEE6");   // 구역 가장자리가 빈 종이로 이어지게(블렌더 3차)
            cam.nearClipPlane = 0.3f; cam.farClipPlane = 420f;
            camGo.AddComponent<AudioListener>();
            var urpCam = camGo.AddComponent<UniversalAdditionalCameraData>();
            urpCam.renderPostProcessing = true;
            urpCam.antialiasing = AntialiasingMode.SubpixelMorphologicalAntiAliasing;
            var fc = camGo.AddComponent<FollowCamera>();
            fc.baseView = new FollowCamera.View { yaw = tune.cameraYaw, pitch = tune.cameraPitch, distance = tune.cameraDistance, fov = tune.cameraFov, offset = new Vector3(0, 0.6f, 0) };
            fc.followTime = tune.cameraFollowTime;
            fc.target = player.transform;

            // 후처리: 은은한 번짐(등불·빛줄기), 종이 가장자리 비네트
            var volGo = new GameObject("Post");
            var vol = volGo.AddComponent<Volume>(); vol.isGlobal = true;
            var profPath = "Assets/Game/Settings/OUAT_Post.asset";
            var prof = AssetDatabase.LoadAssetAtPath<VolumeProfile>(profPath);
            if (!prof) { prof = ScriptableObject.CreateInstance<VolumeProfile>(); AssetDatabase.CreateAsset(prof, profPath); }
            if (!prof.TryGet<Bloom>(out var bloom)) bloom = prof.Add<Bloom>(true);
            bloom.intensity.Override(0.6f); bloom.threshold.Override(1.05f); bloom.scatter.Override(0.6f);
            if (!prof.TryGet<Vignette>(out var vig)) vig = prof.Add<Vignette>(true);
            vig.intensity.Override(0.28f); vig.smoothness.Override(0.5f); vig.color.Override(Hex("3A3530"));
            if (!prof.TryGet<ColorAdjustments>(out var ca)) ca = prof.Add<ColorAdjustments>(true);
            ca.saturation.Override(-6f); ca.contrast.Override(6f);
            EditorUtility.SetDirty(prof);
            vol.sharedProfile = prof;

            var uiGo = new GameObject("UI");
            var doc = uiGo.AddComponent<UIDocument>();
            doc.panelSettings = AssetDatabase.LoadAssetAtPath<PanelSettings>(ProjectSetup.PanelSettingsPath);
            var ui = uiGo.AddComponent<UIRoot>();
            ui.styleSheet = AssetDatabase.LoadAssetAtPath<StyleSheet>("Assets/Game/Resources/UI/ouat.uss");
            ui.fontRegular = AssetDatabase.LoadAssetAtPath<FontAsset>("Assets/Game/Resources/UI/Fonts/Pretendard-Regular SDF.asset");
            ui.fontBold = AssetDatabase.LoadAssetAtPath<FontAsset>("Assets/Game/Resources/UI/Fonts/Pretendard-SemiBold SDF.asset");

            var sys = new GameObject("Game");
            sys.AddComponent<AudioHub>();
            sys.AddComponent<GuideSystem>();
            sys.AddComponent<AreaSystem>();
            var director = sys.AddComponent<Director>();
            director.fish = fish;
            director.lightShaft = propObjects.TryGetValue("light_beam", out var lb) ? lb.transform : null;
            director.stageCenter = propObjects.TryGetValue("stage", out var st) ? st.transform : null;
            var game = sys.AddComponent<Game>();
            game.player = player.GetComponent<PlayerMover>();
            game.followCamera = fc;
            game.ui = ui;
            game.director = director;
        }

        // ── 글꼴·조절값 ─────────────────────────────────
        static void EnsureFonts()
        {
            ProjectSetup.EnsureFolder("Assets/Game/Resources/UI/Fonts");
            foreach (var n in new[] { "Pretendard-Regular", "Pretendard-SemiBold", "Pretendard-Bold" })
            {
                var path = $"Assets/Game/Resources/UI/Fonts/{n} SDF.asset";
                if (AssetDatabase.LoadAssetAtPath<FontAsset>(path)) continue;
                var font = AssetDatabase.LoadAssetAtPath<Font>($"Assets/Game/Art/Fonts/{n}.ttf");
                if (!font) continue;
                var fa = FontAsset.CreateFontAsset(font, 64, 6, UnityEngine.TextCore.LowLevel.GlyphRenderMode.SDFAA, 2048, 2048, AtlasPopulationMode.Dynamic, true);
                fa.name = n + " SDF";
                AssetDatabase.CreateAsset(fa, path);
                if (fa.atlasTextures != null) foreach (var t in fa.atlasTextures) if (t && !AssetDatabase.Contains(t)) AssetDatabase.AddObjectToAsset(t, fa);
                if (fa.material && !AssetDatabase.Contains(fa.material)) AssetDatabase.AddObjectToAsset(fa.material, fa);
            }
            AssetDatabase.SaveAssets();
        }

        static void EnsureTuning()
        {
            var path = "Assets/Game/Resources/OUAT_Tuning.asset";
            if (AssetDatabase.LoadAssetAtPath<GameTuning>(path)) return;
            AssetDatabase.CreateAsset(ScriptableObject.CreateInstance<GameTuning>(), path);
        }
    }
}
