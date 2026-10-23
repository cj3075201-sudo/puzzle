# OUAT.Jigsaw — 직소 언어 핵심 (core.js 이식)

원본: `기록/초록테두리_무색모형_2026-10-20/core.js`(+ state.js의 BLUE_WORDS·합성 표 형식). UnityEngine을 쓰지 않는 순수 C#(.NET Standard 2.1, C# 9). 결과는 core.js와 같다(아래 검사).

## API
| 형 | 쓰임 |
|---|---|
| `ModelLibrary.Load(text)` | `Resources/Jigsaw/models.json` 읽기. `Models`(id→모형), `InOrder`(JS 순서), `Palette` |
| `JigsawModel` | `Id` `Color` `Ports` `SocketSides` `Path` `Outline`(셀 0..100, y 아래 다각형 목록) `IsUsable` `TryGetPort` |
| `PathParser` | `ParseSubpaths` / `ParsePolygon`. 파일에 실제로 있는 명령은 M·L·Z뿐이라 그것만 받음. 그리기는 `단위/100` 배율 |
| `PieceLabelLayout` | app.js처럼 홈 쪽을 피한 글자 중심·글자 크기 |
| `Piece(id, modelId, word, x, y)` | 판 위 조각. 빈 모형은 word null 또는 "" |
| `JigsawCore.Analyze(pieces, lib, blueWords, options)` | 판 → `AnalyzeResult { Ok, Code, Message, Canonical, Tree(SpecNode), AnalyzedTree(색·조각 id·테두리 정보), Joints, Groups, FailedGroup }` |
| `JigsawCore.Build(spec, lib, blueWords)` | spec → 조립된 조각 목록(크리처 문장 보여 주기). 실패하면 `JigsawBuildException`(core.js 문구). `TryBuild`도 있음 |
| `JigsawCore.Canonical` / `Eq` / `FindModel` / `Signature` / `LocalEdges` / `CheckGroup` / `ColorOf` | core.js 같은 이름 함수 |
| `SpecNode` | `Word`, `Children`, `FromJson(object)`(`["밖",["몸",["절하다"]]]` 등 세 형식), `Parse(text)`, `Chain("밖","몸",…)`, `Canonical()` |
| `MiniJson` | `Parse`(Dictionary/List/string/double/bool/null), `ParseNode`(키 순서 유지), `Quote`(JSON.stringify와 같은 따옴표) |
| `WordColors` | `ColorOf`(enum), `DefaultBlueWords`, `CreateBlueSet`, `BlueSetFromColors`(챕터 낱말 표 → 파랑 집합), 조각 색 hex |
| `JigsawCodes` | 오류 코드 문자열(core.js와 같음) |

- 파랑 낱말: `ISet<string>`. null이면 `WordColors.DefaultBlueWords`(core.js 기본 + state.js BLUE_WORDS). **1챕터 파랑 낱말 절하다·고르다·데려가다·그리다는 기본 목록에 없다.** 챕터 데이터의 색으로 `BlueSetFromColors`를 만들어 넘길 것. 기본 목록으로 넘기면 「밖→몸→절하다→안→몸」 등 5문장이 chain_limit(노랑 4개 연속)로 실패한다.
- 선형 사슬 A→B→C는 `["A",["B",["C"]]]`(앞 조각 돌출 → 뒤 조각 홈, 접합 방향으로 읽음). 1챕터 15문장 모두 기존 모형으로 만들어진다.
- `AnalyzeOptions`: `Groups`(초록 테두리, 1챕터 없음), `Lexicon`(합성 표), `BoardWidth`/`BoardHeight`(기본 7×6; 대화 판 크기용으로 추가). `Build`는 core.js대로 7×6, 뿌리 (0,2) 고정.

## 검사 실행
```
cd tools/jigsaw-tests
node gen-vectors.js                 # 원본 core.js로 expected/vectors.json 생성 (시험판 경로는 JIGSAW_TRIAL로 바꿀 수 있음)
"/mnt/c/Program Files/dotnet/dotnet.exe" run --project runner
```
`lib/`는 이 폴더의 .cs를 복사하지 않고 링크해 netstandard2.1·C# 9·경고=오류·XML 주석 필수로 컴파일한다. bin/obj는 tools 아래에만 생긴다. 2026-10-22 결과: 5044개 통과, 실패 0.

## 1:1로 옮기지 않은 것
- 기본 파랑 목록: core.js는 자기 목록만, C#은 core + state.js 합집합(요청 사항).
- JS에서만 가능한 입력은 표현할 수 없다: 소수 좌표, 숫자 id, 배열이 아닌 포트(JS는 예외), `"toString"` 같은 프로토타입 키. 깨진 모형 데이터는 C#에서 "쓸 수 없는 모형"(invalid_model)으로 처리한다.
- `root_count`는 코드로 옮겼지만 앞 검사(연결·고리·부모 둘)를 통과하면 원본에서도 나올 수 없다. `branch_limit`은 돌출 4개 모형이 없어 기본 모형으로는 안 나온다(시험용 모형으로 검사).
- `AnalyzeOptions.BoardWidth/Height`, `PieceLabelLayout`, `Outline`은 원본 core.js에 없는 추가 기능.
- 이 폴더에는 asmdef가 없다(Assembly-CSharp에 들어감). UnityEngine 참조는 없으므로 필요하면 `noEngineReferences: true` asmdef로 묶어도 된다.
