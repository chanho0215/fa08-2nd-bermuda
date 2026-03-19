"use client"

import { CarFront, Sparkles, TrendingUp, CircleDollarSign, Zap, ChevronRight } from "lucide-react"

interface WelcomeScreenProps {
  onStart: () => void
}

export function WelcomeScreen({ onStart }: WelcomeScreenProps) {
  return (
    <div className="flex flex-col min-h-screen bg-background">
      {/* Header */}
      <header className="px-6 pt-8 pb-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
            <CarFront className="w-4 h-4 text-primary-foreground" />
          </div>
          <span className="text-sm font-semibold text-primary">당근</span>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 px-6 pt-4 pb-8">
        {/* Title Section */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-foreground leading-tight mb-3">
            자동차 판매가격
            <br />
            예측 서비스
          </h1>
          <p className="text-base text-muted-foreground leading-relaxed">
            차량 정보를 입력하면 AI가 분석하여
            <br />
            <span className="text-foreground font-medium">빠른 판매가, 적정 판매가, 최대 수익가</span>를
            <br />
            추천해드려요.
          </p>
        </div>

        {/* Feature Cards */}
        <div className="space-y-3 mb-8">
          <div className="flex items-start gap-4 p-4 bg-card rounded-2xl border border-border">
            <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center shrink-0">
              <Zap className="w-5 h-5 text-blue-600" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-foreground mb-1">빠른 판매가</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                빠르게 거래하고 싶을 때 적합한 가격이에요
              </p>
            </div>
          </div>

          <div className="flex items-start gap-4 p-4 bg-card rounded-2xl border border-border">
            <div className="w-10 h-10 bg-orange-50 rounded-xl flex items-center justify-center shrink-0">
              <CircleDollarSign className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-foreground mb-1">적정 판매가</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                시세와 차량 조건을 반영한 균형 잡힌 가격이에요
              </p>
            </div>
          </div>

          <div className="flex items-start gap-4 p-4 bg-card rounded-2xl border border-border">
            <div className="w-10 h-10 bg-green-50 rounded-xl flex items-center justify-center shrink-0">
              <TrendingUp className="w-5 h-5 text-green-600" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-foreground mb-1">최대 수익가</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                여유 있게 최고 가격을 노려볼 수 있어요
              </p>
            </div>
          </div>
        </div>

        {/* Illustration Area */}
        <div className="relative flex items-center justify-center py-6">
          <div className="relative">
            <div className="w-32 h-32 bg-primary/10 rounded-full flex items-center justify-center">
              <CarFront className="w-16 h-16 text-primary" />
            </div>
            <div className="absolute -top-2 -right-2 w-10 h-10 bg-primary rounded-full flex items-center justify-center shadow-lg shadow-primary/30">
              <Sparkles className="w-5 h-5 text-primary-foreground" />
            </div>
          </div>
        </div>
      </main>

      {/* Bottom Section */}
      <div className="px-6 pb-8">
        {/* Start Button */}
        <button
          type="button"
          onClick={onStart}
          className="w-full h-14 bg-primary text-primary-foreground font-semibold rounded-2xl shadow-lg shadow-primary/20 hover:bg-primary/90 transition-all flex items-center justify-center gap-2"
        >
          <span>시작하기</span>
          <ChevronRight className="w-5 h-5" />
        </button>

        {/* Disclaimer */}
        <p className="mt-4 text-xs text-muted-foreground text-center leading-relaxed px-2">
          예측 결과는 참고용이며, 실제 판매가는 차량 상태와
          <br />
          시장 상황에 따라 달라질 수 있습니다.
        </p>
      </div>
    </div>
  )
}
