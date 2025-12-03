import { Radar, RadarChart as RechartsRadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';

interface RadarChartProps {
  scores: {
    semanticReduction: number;
    interpretiveExtension: number;
    lexicalColoring: number;
  };
}

export function RadarChart({ scores }: RadarChartProps) {
  const data = [
    {
      subject: 'Semantic',
      value: scores.semanticReduction,
      fullMark: 100,
    },
    {
      subject: 'Interpretive',
      value: scores.interpretiveExtension,
      fullMark: 100,
    },
    {
      subject: 'Lexical',
      value: scores.lexicalColoring,
      fullMark: 100,
    },
  ];

  return (
    <ResponsiveContainer width={128} height={128}>
      <RechartsRadarChart data={data}>
        <PolarGrid stroke="#E0E0E0" />
        <PolarAngleAxis
          dataKey="subject"
          tick={{ fill: '#616161', fontSize: 10 }}
        />
        <PolarRadiusAxis angle={90} domain={[0, 100]} tick={false} />
        <Radar
          name="Distortion"
          dataKey="value"
          stroke="#3D5AFE"
          fill="#3D5AFE"
          fillOpacity={0.5}
        />
      </RechartsRadarChart>
    </ResponsiveContainer>
  );
}