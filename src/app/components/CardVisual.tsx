import { Card } from '../data/mockData';

interface CardVisualProps {
  card: Card;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function CardVisual({ card, size = 'md', className = '' }: CardVisualProps) {
  const dimensions = {
    sm: { width: 'w-28', height: 'h-[70px]', textName: 'text-[9px]', textNum: 'text-[8px]', chip: 'w-5 h-4' },
    md: { width: 'w-48', height: 'h-[115px]', textName: 'text-[11px]', textNum: 'text-[10px]', chip: 'w-8 h-6' },
    lg: { width: 'w-72', height: 'h-[172px]', textName: 'text-sm', textNum: 'text-xs', chip: 'w-12 h-9' },
  };

  const d = dimensions[size];

  return (
    <div
      className={`${d.width} ${d.height} rounded-xl relative overflow-hidden shadow-lg flex-shrink-0 ${className}`}
      style={{ background: card.gradient }}
    >
      {/* Shine effect */}
      <div className="absolute inset-0 opacity-20"
        style={{
          background: 'radial-gradient(ellipse at 20% 20%, rgba(255,255,255,0.6) 0%, transparent 60%)'
        }}
      />
      {/* Network logo area */}
      <div className={`absolute top-3 right-3 ${d.textNum} font-bold text-white/80 tracking-wider`}>
        {card.network}
      </div>
      {/* Chip */}
      <div className={`absolute left-4 top-1/2 -translate-y-1/2 ${d.chip} rounded-sm bg-yellow-300/70 border border-yellow-200/50`}
        style={{
          background: 'linear-gradient(135deg, #f9e784 0%, #e6c84f 50%, #f9e784 100%)'
        }}
      >
        <div className="w-full h-full grid grid-cols-2 gap-[1px] p-[2px] opacity-60">
          <div className="bg-yellow-600/40 rounded-[1px]" />
          <div className="bg-yellow-600/40 rounded-[1px]" />
          <div className="bg-yellow-600/40 rounded-[1px]" />
          <div className="bg-yellow-600/40 rounded-[1px]" />
        </div>
      </div>
      {/* Card number */}
      {size !== 'sm' && (
        <div className={`absolute bottom-8 left-4 right-4 ${d.textNum} text-white/60 font-mono tracking-widest`}>
          •••• •••• •••• 1234
        </div>
      )}
      {/* Card name */}
      <div className={`absolute bottom-3 left-4 right-4`}>
        <div className={`${d.textName} text-white/90 font-medium truncate`}>{card.name}</div>
      </div>
      {/* Decorative circle */}
      <div className="absolute -bottom-8 -right-8 w-24 h-24 rounded-full bg-white/5" />
      <div className="absolute -bottom-4 -right-4 w-16 h-16 rounded-full bg-white/5" />
    </div>
  );
}
