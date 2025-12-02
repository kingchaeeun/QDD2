import { createRoot } from "react-dom/client";
import "../styles/index.css";

function Popup() {
  return (
    <div className="min-h-[320px] w-[360px] p-5 bg-white text-gray-800">
      <h1 className="text-xl font-semibold mb-3">Quote Distortion Detector</h1>
      <p className="text-sm leading-relaxed mb-4">
        이 확장 프로그램은 별도의 팝업 없이&nbsp;
        <span className="font-semibold text-[#3D5AFE]">네이버 모바일 기사</span>에서 자동으로 실행됩니다.
      </p>

      <ol className="space-y-2 text-sm list-decimal list-inside">
        <li>새 탭에서&nbsp;
          <span className="font-semibold">https://n.news.naver.com/mnews/article/&lt;언론사코드&gt;/&lt;기사번호&gt;</span>
          &nbsp;형식의 기사를 엽니다.</li>
        <li>페이지가 로드되면 오른쪽에 QDD 패널이 자동으로 나타납니다.</li>
        <li>필요 시 인용문을 클릭하여 패널을 다시 열 수 있습니다.</li>
      </ol>

      <p className="text-xs text-gray-500 mt-5">
        팝업은 테스트용으로만 남겨두었으며, 실제 기능은 기사 페이지에서만 제공됩니다.
      </p>
    </div>
  );
}

const root = document.getElementById("root");
if (root) {
  createRoot(root).render(<Popup />);
}

