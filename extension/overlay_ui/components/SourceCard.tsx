import { ExternalLink } from "lucide-react";
import { RadarChart } from "./RadarChart";
import { useState } from "react";
import { Languages } from "lucide-react";

interface SourceCardProps {
  source: {
    id: number;
    title: string;
    sourceLink: string;
    originalText: string;
    distortionScore: number;
    similarityScore: number;
    scores: {
      semanticReduction: number;
      interpretiveExtension: number;
      lexicalColoring: number;
    };
  };
  onViewSource: (source: any) => void;
}

// Korean translations for each source
const koreanTranslations: { [key: number]: string } = {
  1: "우리는 이야기를 나누었는데, 그건 한국에게는 큰 문제였지 일본에게는 아니었습니다. 일본은 가고 싶어 했고, 따라잡고 싶어 했지만 한국은 그 부분에서 매우 어려움을 겪었습니다. 이해하시나요? 그래서 잘 모르겠네요. 아마 대답해 주시면 좋을 것 같습니다.",
  2: '전직 대통령은 한국 협상의 어려움을 언급했습니다. "우리가 해결해야 할 문제들이 있었지만, 합의에 도달할 수 있다고 믿습니다"라고 트럼프는 기자들에게 말했습니다. 그의 발언은 무역 관계자들과의 2시간 회의 후에 나왔습니다.',
  3: '트럼프는 인터뷰에서 한국 상황의 복잡성을 인정했습니다. "그것은 협상의 가장 어려운 측면 중 하나였습니다"라고 그는 말하며, 그 과정이 인내를 필요로 한다고 설명했습니다. 그는 수 주에 걸쳐 점진적으로 진전이 있었다고 언급했습니다.',
  4: '백악관 밖에서 기자들에게 한 발언에서 트럼프는 "한국은 협상 과정에서 상당한 장애물을 제시했습니다"라고 말했습니다. 그는 구체적인 문제에 대해 자세히 설명하지 않았습니다. 협상에 가까운 소식통은 관세 구조가 주요 관심사였다고 시사했습니다.',
  5: '트럼프는 각료 회의에서 한국 관련 논의의 어려운 성격에 대해 언급했습니다. "우리는 초기 어려움에도 불구하고 진전을 이루었습니다"라고 그는 말하며, 그의 팀이 부지런히 일했다고 덧붙였습니다. 행정부는 구체적인 협상 세부 사항에 대해 입을 다물고 있습니다.',
  6: '서명식에서 메르켈 총리는 "이 협정은 회원국 간의 협력 관계를 촉진하는 데 있어 중요한 진전을 의미합니다"라고 선언했습니다. 그녀는 상호 이익을 강조했습니다. 그녀의 연설은 이 이정표에 도달하는 데 필요한 수년간의 외교적 노력을 강조했습니다.',
  7: '총리는 참여국들이 강화된 경제 조정으로부터 혜택을 받을 것이라고 강조했습니다. "우리는 지속적인 협력을 위한 프레임워크를 만들었습니다"라고 메르켈은 정상회의에서 말했습니다. 경제 분석가들은 협정의 포괄적인 성격을 칭찬했습니다.',
  8: '메르켈은 이 거래가 국제 파트너십을 위한 새로운 기회를 여는 것이라고 설명했습니다. "이것은 국경을 넘어 공동 번영으로 가는 문을 엽니다"라고 그녀는 모인 대표들에게 말했습니다. 총리는 발언 후 기립 박수를 받았습니다.',
  9: '연설에서 총리는 다자간 프레임워크에서 발생하는 상호 이점에 대해 말했습니다. "모든 당사자가 이 협력적 접근 방식으로부터 이익을 얻을 것입니다"라고 메르켈은 기자들에게 설명했습니다. 그녀는 외교적 모멘텀을 유지하는 것의 중요성을 강조했습니다.',
  10: '메르켈은 모든 서명국에 걸쳐 강화된 유대의 잠재력을 강조했습니다. "이것은 상호 혜택과 더 깊은 통합을 나타냅니다"라고 그녀는 기자회견에서 말했습니다. 독일 관계자들은 이행이 2026년 초에 시작될 것이라고 밝혔습니다.',
};

export function SourceCard({
  source,
  onViewSource,
}: SourceCardProps) {
  const [isTranslated, setIsTranslated] = useState(false);

  const getScoreColor = (score: number) => {
    if (score >= 70) return "text-red-600";
    if (score >= 50) return "text-orange-600";
    return "text-green-600";
  };

  return (
    <div className="bg-white border-2 border-gray-200 rounded-2xl p-5 shadow-md">
      {/* Card Title */}
      <h3 className="mb-3 text-gray-800">{source.title}</h3>

      {/* Source Link */}
      <a
        href={source.sourceLink}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-1 text-[#3D5AFE] underline mb-4 hover:text-blue-700 transition-colors"
      >
        <span className="break-all">
          {source.sourceLink.length > 60
            ? `${source.sourceLink.slice(0, 40)}...${source.sourceLink.slice(-20)}`
            : source.sourceLink}
        </span>
        <ExternalLink className="w-4 h-4 flex-shrink-0" />
      </a>

      {/* Original Text */}
      <div className="bg-[#F1F3F4] rounded-lg p-3 mb-4 relative">
        <p className="text-gray-700 pr-8">
          {isTranslated
            ? koreanTranslations[source.id]
            : source.originalText}
        </p>
        <button
          onClick={() => setIsTranslated(!isTranslated)}
          className="absolute bottom-2 right-2 p-1.5 hover:bg-gray-300 rounded-lg transition-colors"
          title={isTranslated ? "원문 보기" : "한국어로 번역"}
        >
          <Languages className="w-4 h-4 text-gray-600" />
        </button>
      </div>

      {/* Similarity Score */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-gray-700">
            유사도 점수 (신뢰도)
          </span>
          <span
            className={`${
              source.similarityScore >= 80
                ? "text-green-600"
                : source.similarityScore >= 70
                  ? "text-blue-600"
                  : "text-orange-600"
            }`}
          >
            {source.similarityScore}/100
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className={`h-2 rounded-full ${
              source.similarityScore >= 80
                ? "bg-green-600"
                : source.similarityScore >= 70
                  ? "bg-blue-600"
                  : "bg-orange-600"
            }`}
            style={{ width: `${source.similarityScore}%` }}
          />
        </div>
      </div>

      {/* Distortion Score */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-gray-700">왜곡 점수</span>
          <span
            className={`${getScoreColor(source.distortionScore)}`}
          >
            {source.distortionScore}/100
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className={`h-2 rounded-full ${
              source.distortionScore >= 70
                ? "bg-red-600"
                : source.distortionScore >= 50
                  ? "bg-orange-600"
                  : "bg-green-600"
            }`}
            style={{ width: `${source.distortionScore}%` }}
          />
        </div>
      </div>

      {/* Sub-scores with Radar Chart */}
      <div className="mb-5">
        <h4 className="text-gray-700 mb-3">세부 점수 분석</h4>
        <div className="flex items-start gap-4">
          <div className="flex-1 space-y-2">
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-gray-600">의미 축소</span>
                <span
                  className={getScoreColor(
                    source.scores.semanticReduction,
                  )}
                >
                  {source.scores.semanticReduction}
                </span>
              </div>
            </div>
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-gray-600">해석 확장</span>
                <span
                  className={getScoreColor(
                    source.scores.interpretiveExtension,
                  )}
                >
                  {source.scores.interpretiveExtension}
                </span>
              </div>
            </div>
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-gray-600">어휘 색채</span>
                <span
                  className={getScoreColor(
                    source.scores.lexicalColoring,
                  )}
                >
                  {source.scores.lexicalColoring}
                </span>
              </div>
            </div>
          </div>
          <div className="w-32 h-32 flex-shrink-0">
            <RadarChart scores={source.scores} />
          </div>
        </div>
      </div>

      {/* View Source Button */}
      <button
        onClick={() => onViewSource(source)}
        className="w-full py-3 bg-[#3D5AFE] text-white rounded-xl hover:bg-blue-700 transition-colors"
      >
        원문 보기
      </button>
    </div>
  );
}