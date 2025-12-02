import { ImageWithFallback } from "./figma/ImageWithFallback";
import { detectedQuotes, isQuoteDistorted } from "../data/quotesData";

interface NewsArticleProps {
  onQuoteClick: (quoteIndex: number) => void;
  highlightSettings: {
    distorted: boolean;
    normal: boolean;
  };
  isPanelOpen: boolean;
}

export function NewsArticle({ onQuoteClick, highlightSettings, isPanelOpen }: NewsArticleProps) {
  // 하이라이트 적용 여부 결정: 왜곡 점수 기반 판정
  const shouldHighlight = (index: number) => {
    const quote = detectedQuotes[index];
    const isDistorted = isQuoteDistorted(quote);
    
    if (isDistorted) {
      return highlightSettings.distorted;
    } else {
      return highlightSettings.normal;
    }
  };

  return (
    <div className="min-h-screen bg-[#FAFAFA] relative">
      {/* Scroll Indicator */}
      <div className="fixed right-0 top-0 h-full w-1 bg-gray-200">
        <div className="h-1/3 w-full bg-[#3D5AFE]" />
      </div>

      {/* Article Content */}
      <div className={`px-12 py-8 transition-all duration-300 ${
        isPanelOpen ? 'max-w-[900px]' : 'w-full'
      }`}>
        {/* Header */}
        <header className="mb-12 pb-6 border-b-2 border-gray-300">
          <div
            style={{
              fontFamily:
                "'Noto Serif KR', 'Nanum Myeongjo', serif",
              fontWeight: 700,
              fontSize: "32px",
              color: "#000000",
              letterSpacing: "0px",
            }}
          >
            경향신문
          </div>
        </header>

        {/* Article Title */}
        <h1 className="mb-6 text-2xl font-medium flex items-start gap-1">
          <span className="whitespace-nowrap">트럼프</span>
          <span className="relative inline-block leading-snug">
            <span
              className={`relative inline-block cursor-pointer transition-colors ${
                shouldHighlight(0) ? "bg-yellow-200 hover:bg-yellow-300" : "hover:bg-yellow-200 rounded"
              }`}
              onClick={() => onQuoteClick(0)}
            >
              "한국, 위안부 문제에 집착"
              <sup className="text-[10px] text-black ml-0.5">1</sup>
            </span>
            …
            <span
              className={`relative inline-block cursor-pointer transition-colors ${
                shouldHighlight(1) ? "bg-yellow-200 hover:bg-yellow-300" : "hover:bg-yellow-200 rounded"
              }`}
              onClick={() => onQuoteClick(1)}
            >
              "일본, 훌륭한 나라"
              <sup className="text-[10px] text-black ml-0.5">2</sup>
            </span>
          </span>
        </h1>

        {/* Journalist Info */}
        <div className="text-gray-600 mb-8 pb-6 border-b border-gray-300">
          <span>윤기은 기자</span>
          <span className="mx-2">•</span>
          <span>2025년 8월 26일</span>
          <span className="mx-2">•</span>
          <span>국제</span>
        </div>

        {/* Subheadline */}
        <div className="mb-8 pl-4 border-l-4 border-gray-800 py-3 space-y-1">
          <p className="leading-relaxed">
            <span
              className={`relative inline-block cursor-pointer transition-colors ${
                shouldHighlight(2) ? "bg-yellow-200 hover:bg-yellow-300" : "hover:bg-yellow-200 rounded"
              }`}
              onClick={() => onQuoteClick(2)}
            >
              "일본은 앞으로 나아가고 싶어 해"
              <sup className="text-[10px] text-black ml-0.5">3</sup>
            </span>
          </p>
          <p className="leading-relaxed">
            <span
              className={`relative inline-block cursor-pointer transition-colors ${
                shouldHighlight(3) ? "bg-yellow-200 hover:bg-yellow-300" : "hover:bg-yellow-200 rounded"
              }`}
              onClick={() => onQuoteClick(3)}
            >
              "양국 간 장애물 내 임기 동안 제거"
              <sup className="text-[10px] text-black ml-0.5">4</sup>
            </span>
          </p>
          <p className="leading-relaxed">
            <span
              className={`relative inline-block cursor-pointer transition-colors ${
                shouldHighlight(4) ? "bg-yellow-200 hover:bg-yellow-300" : "hover:bg-yellow-200 rounded"
              }`}
              onClick={() => onQuoteClick(4)}
            >
              "위대한 아베, 한국에 따뜻한 감정"
              <sup className="text-[10px] text-black ml-0.5">5</sup>
            </span>
          </p>
        </div>

        {/* Image */}
        <figure className="mb-8">
          <ImageWithFallback
            src="https://img.khan.co.kr/news/r/700xX/2025/08/26/news-p.v1.20250821.d2ab2afd360e40b2b0c62d38c4feec22_P1.webp"
            alt="일본대사관 앞 소녀상"
            className="w-full h-auto object-cover rounded-lg"
          />
          <figcaption className="text-gray-600 text-center mt-3">
            이재명 대통령이 취임 후 첫 일본 방문을 앞두고
            '위안부' 합의, 강제동원 배상 문제에 대해 뒤집는 것은
            바람직하지 않다는 입장을 밝힌 21일 서울 종로구
            일본대사관 앞 소녀상. 정효진 기자
          </figcaption>
        </figure>

        {/* Article Body */}
        <div className="space-y-6">
          <p>
            이재명 대통령과 정상회담한 도널드 트럼프 미국
            대통령이{" "}
            <span
              className={`relative inline-block cursor-pointer transition-colors ${
                shouldHighlight(5) ? "bg-yellow-200 hover:bg-yellow-300" : "hover:bg-yellow-200 rounded"
              }`}
              onClick={() => onQuoteClick(5)}
            >
              "한국이 위안부 문제에 매우 집착"
              <sup className="text-[10px] text-black ml-0.5">6</sup>
            </span>
            해서 한·일 관계 개선에 어려움을 겪었다고 말했다.
          </p>

          <p>
            트럼프 대통령은 25일(현지시간) 워싱턴 백악관에서
            열린 이 대통령과의 정상회담에서{" "}
            <span 
              className={`relative inline-block cursor-pointer transition-colors ${
                shouldHighlight(6) ? "bg-yellow-200 hover:bg-yellow-300" : "hover:bg-yellow-200 rounded"
              }`}
              onClick={() => onQuoteClick(6)}
            >
              "한국이 아직 위안부를 생각하고 있어서 내가 두
              나라가 함께 하도록 만드는 데 다소 어려움을
              겪었다"
              <sup className="text-[10px] text-black ml-0.5">7</sup>
            </span>
            고 밝혔다. 그러면서{" "}
            <span 
              className={`relative inline-block cursor-pointer transition-colors ${
                shouldHighlight(7) ? "bg-yellow-200 hover:bg-yellow-300" : "hover:bg-yellow-200 rounded"
              }`}
              onClick={() => onQuoteClick(7)}
            >
              "나는 그것이 수십 년 동안 몇 차례 해결된 줄
              알았다"
              <sup className="text-[10px] text-black ml-0.5">8</sup>
            </span>
            며{" "}
            <span 
              className={`relative inline-block cursor-pointer transition-colors ${
                shouldHighlight(8) ? "bg-yellow-200 hover:bg-yellow-300" : "hover:bg-yellow-200 rounded"
              }`}
              onClick={() => onQuoteClick(8)}
            >
              "그러나 거기에는 중첩된 문제가 있다"
              <sup className="text-[10px] text-black ml-0.5">9</sup>
            </span>
            고 말했다.
          </p>

          <p>
            그는{" "}
            <span
              className={`relative inline-block cursor-pointer transition-colors ${
                shouldHighlight(9) ? "bg-yellow-200 hover:bg-yellow-300" : "hover:bg-yellow-200 rounded"
              }`}
              onClick={() => onQuoteClick(9)}
            >
              "내가 잘못 말하는 것일 수도 있고 맞지 않을 수도
              있는데 그것은 일본은 아니지만, 한국에 매우 큰
              문제였다"
              <sup className="text-[10px] text-black ml-0.5">10</sup>
            </span>
            며{" "}
            <span
              className={`relative inline-block cursor-pointer transition-colors ${
                shouldHighlight(10) ? "bg-yellow-200 hover:bg-yellow-300" : "hover:bg-yellow-200 rounded"
              }`}
              onClick={() => onQuoteClick(10)}
            >
              "일본은 앞으로 나아가고 싶어 한다. 그러나 한국은
              그 문제에 매우 집착했다"
              <sup className="text-[10px] text-black ml-0.5">11</sup>
            </span>
            고 말했다. 이어{" "}
            <span
              className={`relative inline-block cursor-pointer transition-colors ${
                shouldHighlight(11) ? "bg-yellow-200 hover:bg-yellow-300" : "hover:bg-yellow-200 rounded"
              }`}
              onClick={() => onQuoteClick(11)}
            >
              "오래전에 일어난 일 때문에 일본과 한국을
              함께하게 하는 게 어려웠다"
              <sup className="text-[10px] text-black ml-0.5">12</sup>
            </span>
            면서{" "}
            <span
              className={`relative inline-block cursor-pointer transition-colors ${
                shouldHighlight(12) ? "bg-yellow-200 hover:bg-yellow-300" : "hover:bg-yellow-200 rounded"
              }`}
              onClick={() => onQuoteClick(12)}
            >
              "일본은 그렇게 하고 싶어 하지만 한국은 그보다
              다소 미온적"
              <sup className="text-[10px] text-black ml-0.5">13</sup>
            </span>
            이라고 말했다.
          </p>

          <p>
            트럼프 대통령은{" "}
            <span 
              className={`relative inline-block cursor-pointer transition-colors ${
                shouldHighlight(13) ? "bg-yellow-200 hover:bg-yellow-300" : "hover:bg-yellow-200 rounded"
              }`}
              onClick={() => onQuoteClick(13)}
            >
              "일본은 한국과 매우 잘 지내고 싶어 한다.
              (일본인은) 훌륭한 국민이고 (일본은) 훌륭한
              나라라고 생각한다"
              <sup className="text-[10px] text-black ml-0.5">14</sup>
            </span>
            면서{" "}
            <span 
              className={`relative inline-block cursor-pointer transition-colors ${
                shouldHighlight(14) ? "bg-yellow-200 hover:bg-yellow-300" : "hover:bg-yellow-200 rounded"
              }`}
              onClick={() => onQuoteClick(14)}
            >
              "한국과 일본은 공통점이 있다. 북한 문제를
              해결하고 싶어 한다는 것"
              <sup className="text-[10px] text-black ml-0.5">15</sup>
            </span>
            이라고 덧붙였다.
          </p>

          <p>
            그러면서{" "}
            <span 
              className={`relative inline-block cursor-pointer transition-colors ${
                shouldHighlight(15) ? "bg-yellow-200 hover:bg-yellow-300" : "hover:bg-yellow-200 rounded"
              }`}
              onClick={() => onQuoteClick(15)}
            >
              "두 나라 사이에 존재했던 많은 장애물이 내 임기
              동안 제거됐다"
              <sup className="text-[10px] text-black ml-0.5">16</sup>
            </span>
            고 주장하며{" "}
            <span 
              className={`relative inline-block cursor-pointer transition-colors ${
                shouldHighlight(16) ? "bg-yellow-200 hover:bg-yellow-300" : "hover:bg-yellow-200 rounded"
              }`}
              onClick={() => onQuoteClick(16)}
            >
              "한국이 일본과 훌륭한 관계를 맺을 수 있다고
              생각한다"
              <sup className="text-[10px] text-black ml-0.5">17</sup>
            </span>
            고 말했다.
          </p>

          <p>
            특히 그는 자신과 친분이 두터웠던 고 아베 신조 전
            일본 총리를 두고{" "}
            <span 
              className={`relative inline-block cursor-pointer transition-colors ${
                shouldHighlight(17) ? "bg-yellow-200 hover:bg-yellow-300" : "hover:bg-yellow-200 rounded"
              }`}
              onClick={() => onQuoteClick(17)}
            >
              "그는 위대한 사람이었고 훌륭한 친구였다. 그는
              한국에 대해 매우 따뜻한 감정이 있었다"
              <sup className="text-[10px] text-black ml-0.5">18</sup>
            </span>
            면서{" "}
            <span 
              className={`relative inline-block cursor-pointer transition-colors ${
                shouldHighlight(18) ? "bg-yellow-200 hover:bg-yellow-300" : "hover:bg-yellow-200 rounded"
              }`}
              onClick={() => onQuoteClick(18)}
            >
              "(이시바 시게루) 현 총리도 같은 감정"
              <sup className="text-[10px] text-black ml-0.5">19</sup>
            </span>
            이라고 언급했다.
          </p>
        </div>

        {/* Article Footer */}
        <div className="mt-12 pt-6 border-t border-gray-300 text-gray-600"></div>
      </div>
    </div>
  );
}