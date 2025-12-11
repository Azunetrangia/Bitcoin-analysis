"""
Investment Advisor Service - Multi-factor investment decision engine.

Analyzes multiple factors:
- Trend analysis (price direction, momentum)
- Risk metrics (VaR, Volatility, Sharpe)
- Market regime (Bull/Bear/Neutral/HighVol)
- Technical indicators (RSI, MACD)
- Drawdown analysis
"""

from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np
from enum import Enum


class InvestmentSignal(str, Enum):
    """Investment signal levels."""
    STRONG_BUY = "Mua mạnh"
    BUY = "Mua"
    HOLD = "Giữ"
    SELL = "Bán"
    STRONG_SELL = "Bán mạnh"


class InvestmentAdvisorService:
    """
    Multi-factor investment decision engine.
    
    Combines technical analysis, risk metrics, and market regime
    to provide actionable investment recommendations.
    """
    
    def __init__(self):
        """Initialize the advisor with scoring weights."""
        self.weights = {
            'trend': 0.25,          # Price trend and momentum
            'technical': 0.25,      # RSI, MACD signals
            'risk': 0.20,           # Risk metrics (VaR, Sharpe, Volatility)
            'regime': 0.20,         # Market regime classification
            'drawdown': 0.10        # Current drawdown status
        }
    
    def analyze(self, df: pd.DataFrame, regime_data: pd.DataFrame = None) -> Dict[str, Any]:
        """
        Generate investment recommendation based on multi-factor analysis.
        
        Args:
            df: DataFrame with OHLCV data and technical indicators
            regime_data: DataFrame with regime classifications and probabilities
            
        Returns:
            Dictionary with signal, score, confidence, detailed factors, and actionable insights
        """
        # Calculate individual factor scores (0-100)
        trend_score, trend_details = self._analyze_trend(df)
        technical_score, technical_details = self._analyze_technical_indicators(df)
        risk_score, risk_details = self._analyze_risk_metrics(df)
        regime_score, regime_details = self._analyze_regime(regime_data) if regime_data is not None else (50.0, {})
        drawdown_score, drawdown_details = self._analyze_drawdown(df)
        
        # Calculate market context
        market_context = self._analyze_market_context(df)
        
        # Calculate weighted composite score
        composite_score = (
            self.weights['trend'] * trend_score +
            self.weights['technical'] * technical_score +
            self.weights['risk'] * risk_score +
            self.weights['regime'] * regime_score +
            self.weights['drawdown'] * drawdown_score
        )
        
        # Determine signal based on score thresholds
        signal, confidence = self._score_to_signal(composite_score)
        
        # Generate actionable insights
        insights = self._generate_insights(
            signal=signal,
            trend_details=trend_details,
            technical_details=technical_details,
            risk_details=risk_details,
            regime_details=regime_details,
            drawdown_details=drawdown_details,
            market_context=market_context
        )
        
        # Build detailed breakdown
        factors = {
            'trend': {
                'score': round(trend_score, 2),
                'weight': self.weights['trend'],
                'contribution': round(self.weights['trend'] * trend_score, 2),
                'details': trend_details
            },
            'technical': {
                'score': round(technical_score, 2),
                'weight': self.weights['technical'],
                'contribution': round(self.weights['technical'] * technical_score, 2),
                'details': technical_details
            },
            'risk': {
                'score': round(risk_score, 2),
                'weight': self.weights['risk'],
                'contribution': round(self.weights['risk'] * risk_score, 2),
                'details': risk_details
            },
            'regime': {
                'score': round(regime_score, 2),
                'weight': self.weights['regime'],
                'contribution': round(self.weights['regime'] * regime_score, 2),
                'details': regime_details
            },
            'drawdown': {
                'score': round(drawdown_score, 2),
                'weight': self.weights['drawdown'],
                'contribution': round(self.weights['drawdown'] * drawdown_score, 2),
                'details': drawdown_details
            }
        }
        
        return {
            'signal': signal.value,
            'score': round(composite_score, 2),
            'confidence': round(confidence, 2),
            'factors': factors,
            'market_context': market_context,
            'insights': insights,
            'timestamp': df['timestamp'].iloc[-1] if 'timestamp' in df.columns else pd.Timestamp.now()
        }
    
    def _analyze_trend(self, df: pd.DataFrame) -> Tuple[float, Dict[str, Any]]:
        """
        Analyze price trend and momentum (0-100).
        
        Returns:
            (score, details_dict)
        """
        if len(df) < 20:
            return 50.0, {'status': 'insufficient_data'}
        
        score = 50.0  # Neutral baseline
        details = {}
        
        # Short-term vs long-term price comparison
        recent_prices = df['close'].tail(7).mean()
        older_prices = df['close'].tail(30).mean()
        current_price = df['close'].iloc[-1]
        
        price_change_pct = ((recent_prices - older_prices) / older_prices) * 100
        details['price_change_7d_vs_30d'] = round(price_change_pct, 2)
        
        if recent_prices > older_prices:
            score += min(price_change_pct * 2, 30)
            details['trend_direction'] = 'uptrend'
        else:
            score += max(price_change_pct * 2, -30)
            details['trend_direction'] = 'downtrend'
        
        # Moving average alignment
        if 'sma_20' in df.columns and 'sma_50' in df.columns:
            sma_20 = df['sma_20'].iloc[-1]
            sma_50 = df['sma_50'].iloc[-1]
            
            details['price'] = round(current_price, 2)
            details['sma_20'] = round(sma_20, 2)
            details['sma_50'] = round(sma_50, 2)
            
            # Price position relative to MAs
            if current_price > sma_20 and current_price > sma_50:
                score += 10
                details['ma_position'] = 'above_both'
                details['ma_signal'] = 'bullish'
            elif current_price < sma_20 and current_price < sma_50:
                score -= 10
                details['ma_position'] = 'below_both'
                details['ma_signal'] = 'bearish'
            else:
                details['ma_position'] = 'mixed'
                details['ma_signal'] = 'neutral'
            
            # Golden/Death cross
            if sma_20 > sma_50:
                score += 10
                details['ma_cross'] = 'golden_cross'
            else:
                score -= 10
                details['ma_cross'] = 'death_cross'
        
        # Momentum strength (recent 7 days)
        if len(df) >= 7:
            week_ago_price = df['close'].iloc[-7]
            momentum_pct = ((current_price - week_ago_price) / week_ago_price) * 100
            details['momentum_7d'] = round(momentum_pct, 2)
            
            if abs(momentum_pct) > 10:
                details['momentum_strength'] = 'strong'
            elif abs(momentum_pct) > 5:
                details['momentum_strength'] = 'moderate'
            else:
                details['momentum_strength'] = 'weak'
        
        final_score = np.clip(score, 0, 100)
        details['score_interpretation'] = self._interpret_score(final_score)
        
        return final_score, details
    
    def _analyze_technical_indicators(self, df: pd.DataFrame) -> Tuple[float, Dict[str, Any]]:
        """
        Analyze technical indicators (RSI, MACD) (0-100).
        
        Returns:
            (score, details_dict)
        """
        if len(df) < 26:
            return 50.0, {'status': 'insufficient_data'}
        
        score = 50.0
        details = {}
        
        # RSI analysis
        if 'rsi' in df.columns:
            rsi = df['rsi'].iloc[-1]
            details['rsi'] = round(rsi, 2)
            
            if rsi < 30:
                score += 25
                details['rsi_signal'] = 'oversold_strong_buy'
                details['rsi_interpretation'] = 'Quá bán - Cơ hội mua tốt'
            elif rsi > 70:
                score -= 25
                details['rsi_signal'] = 'overbought_strong_sell'
                details['rsi_interpretation'] = 'Quá mua - Nên chốt lời'
            elif 40 <= rsi <= 60:
                details['rsi_signal'] = 'neutral'
                details['rsi_interpretation'] = 'Trung lập'
            elif rsi < 40:
                score += 10
                details['rsi_signal'] = 'oversold_mild'
                details['rsi_interpretation'] = 'Hơi quá bán'
            elif rsi > 60:
                score -= 10
                details['rsi_signal'] = 'overbought_mild'
                details['rsi_interpretation'] = 'Hơi quá mua'
            
            # RSI divergence check (advanced)
            if len(df) >= 14:
                price_trend = df['close'].iloc[-14:].is_monotonic_increasing
                rsi_trend = df['rsi'].iloc[-14:].is_monotonic_increasing if 'rsi' in df.columns else False
                
                if price_trend and not rsi_trend:
                    details['rsi_divergence'] = 'bearish_divergence'
                    score -= 5
                elif not price_trend and rsi_trend:
                    details['rsi_divergence'] = 'bullish_divergence'
                    score += 5
                else:
                    details['rsi_divergence'] = 'none'
        else:
            details['rsi'] = 'not_available'
        
        # MACD analysis
        if 'macd' in df.columns and 'macd_signal' in df.columns:
            macd = df['macd'].iloc[-1]
            macd_signal = df['macd_signal'].iloc[-1]
            macd_hist = macd - macd_signal
            
            details['macd'] = round(macd, 4)
            details['macd_signal'] = round(macd_signal, 4)
            details['macd_histogram'] = round(macd_hist, 4)
            
            # Current position
            if macd > macd_signal:
                score += 15
                details['macd_position'] = 'bullish'
                details['macd_interpretation'] = 'MACD trên Signal - Xu hướng tăng'
                
                # Check for recent crossover
                if len(df) >= 5:
                    prev_macd = df['macd'].iloc[-5]
                    prev_signal = df['macd_signal'].iloc[-5]
                    if prev_macd <= prev_signal:
                        score += 10
                        details['macd_crossover'] = 'recent_bullish_crossover'
                        details['macd_interpretation'] += ' (Vừa cắt lên)'
                    else:
                        details['macd_crossover'] = 'continued_bullish'
            else:
                score -= 15
                details['macd_position'] = 'bearish'
                details['macd_interpretation'] = 'MACD dưới Signal - Xu hướng giảm'
                
                if len(df) >= 5:
                    prev_macd = df['macd'].iloc[-5]
                    prev_signal = df['macd_signal'].iloc[-5]
                    if prev_macd >= prev_signal:
                        score -= 10
                        details['macd_crossover'] = 'recent_bearish_crossover'
                        details['macd_interpretation'] += ' (Vừa cắt xuống)'
                    else:
                        details['macd_crossover'] = 'continued_bearish'
            
            # MACD histogram strength
            if abs(macd_hist) > abs(df['macd_histogram'].iloc[-10:].mean()) if 'macd_histogram' in df.columns else 0:
                details['macd_strength'] = 'strong'
            else:
                details['macd_strength'] = 'weak'
        else:
            details['macd'] = 'not_available'
        
        final_score = np.clip(score, 0, 100)
        details['score_interpretation'] = self._interpret_score(final_score)
        
        return final_score, details
    
    def _analyze_risk_metrics(self, df: pd.DataFrame) -> Tuple[float, Dict[str, Any]]:
        """
        Analyze risk metrics (VaR, Volatility, Sharpe) (0-100).
        
        Lower risk = higher score (more attractive for investment).
        """
        if len(df) < 30:
            return 50.0, {'status': 'insufficient_data'}
        
        score = 50.0
        details = {}
        
        # Calculate returns
        returns = df['close'].pct_change().dropna()
        
        if len(returns) < 2:
            return 50.0
        
        # Volatility analysis (lower is better)
        volatility = returns.std() * np.sqrt(24)  # Annualized for hourly data
        details['volatility'] = round(volatility * 100, 2)
        
        # Typical crypto volatility: 0.5-2.0 (50-200%)
        if volatility < 0.5:
            score += 20
            details['volatility_level'] = 'very_low'
        elif volatility < 1.0:
            score += 10
            details['volatility_level'] = 'moderate'
        elif volatility > 2.0:
            score -= 20
            details['volatility_level'] = 'very_high'
        elif volatility > 1.5:
            score -= 10
            details['volatility_level'] = 'high'
        else:
            details['volatility_level'] = 'normal'
        
        # Sharpe Ratio (higher is better)
        if len(returns) > 0:
            mean_return = returns.mean()
            std_return = returns.std()
            
            if std_return > 0:
                sharpe = (mean_return / std_return) * np.sqrt(24 * 365)  # Annualized
                details['sharpe_ratio'] = round(sharpe, 2)
                
                if sharpe > 2.0:
                    score += 15
                    details['sharpe_level'] = 'excellent'
                elif sharpe > 1.0:
                    score += 10
                    details['sharpe_level'] = 'good'
                elif sharpe < -1.0:
                    score -= 15
                    details['sharpe_level'] = 'poor'
                elif sharpe < 0:
                    score -= 10
                    details['sharpe_level'] = 'negative'
                else:
                    details['sharpe_level'] = 'fair'
        
        # VaR analysis (95% confidence)
        var_95 = np.percentile(returns, 5)
        details['var_95'] = round(var_95 * 100, 2)
        
        # VaR typically ranges from -0.05 to -0.15 (-5% to -15%)
        if var_95 > -0.03:
            score += 15
            details['var_level'] = 'low_risk'
        elif var_95 > -0.05:
            score += 5
            details['var_level'] = 'moderate_risk'
        elif var_95 < -0.10:
            score -= 15
            details['var_level'] = 'high_risk'
        elif var_95 < -0.07:
            score -= 5
            details['var_level'] = 'elevated_risk'
        else:
            details['var_level'] = 'normal_risk'
        
        final_score = np.clip(score, 0, 100)
        details['score_interpretation'] = self._interpret_score(final_score)
        return final_score, details
    
    def _analyze_regime(self, regime_data: pd.DataFrame) -> Tuple[float, Dict[str, Any]]:
        """
        Analyze market regime (0-100).
        
        Bull regime = high score, Bear = low score.
        """
        if regime_data is None or len(regime_data) == 0:
            return 50.0, {'status': 'no_regime_data'}
        
        # Get latest regime probabilities
        latest = regime_data.iloc[-1]
        
        bull_prob = latest.get('bull_prob', 0.0)
        bear_prob = latest.get('bear_prob', 0.0)
        neutral_prob = latest.get('neutral_prob', 0.0)
        high_vol_prob = latest.get('high_volatility_prob', 0.0)
        
        details = {
            'bull_probability': round(bull_prob * 100, 2),
            'bear_probability': round(bear_prob * 100, 2),
            'neutral_probability': round(neutral_prob * 100, 2),
            'high_volatility_probability': round(high_vol_prob * 100, 2)
        }
        
        # Determine dominant regime
        probs = {'bull': bull_prob, 'bear': bear_prob, 'neutral': neutral_prob, 'high_vol': high_vol_prob}
        dominant = max(probs, key=probs.get)
        details['dominant_regime'] = dominant
        
        # Calculate score based on regime probabilities
        # Bull = 100, Neutral = 50, Bear = 0, HighVol = 30
        score = (
            bull_prob * 100 +
            neutral_prob * 50 +
            bear_prob * 0 +
            high_vol_prob * 30
        )
        
        final_score = np.clip(score, 0, 100)
        details['score_interpretation'] = self._interpret_score(final_score)
        return final_score, details
    
    def _analyze_drawdown(self, df: pd.DataFrame) -> Tuple[float, Dict[str, Any]]:
        """
        Analyze current drawdown status (0-100).
        
        Low drawdown = high score (good entry point).
        """
        if len(df) < 20:
            return 50.0, {'status': 'insufficient_data'}
        
        # Calculate running maximum
        running_max = df['close'].expanding().max()
        drawdown = (df['close'] - running_max) / running_max
        
        current_drawdown = drawdown.iloc[-1]
        max_drawdown = drawdown.min()
        
        details = {
            'current_drawdown': round(current_drawdown * 100, 2),
            'max_drawdown': round(max_drawdown * 100, 2)
        }
        
        score = 50.0
        
        # Current drawdown analysis
        if current_drawdown > -0.05:
            score += 20
            details['drawdown_level'] = 'near_ath'
        elif current_drawdown > -0.10:
            score += 10
            details['drawdown_level'] = 'moderate'
        elif current_drawdown < -0.30:
            score += 15
            details['drawdown_level'] = 'deep_opportunity'
        elif current_drawdown < -0.20:
            score += 5
            details['drawdown_level'] = 'significant'
        else:
            score += 0
            details['drawdown_level'] = 'normal'
        
        # Recovery potential
        recovery_pct = (current_drawdown / max_drawdown) if max_drawdown != 0 else 0
        details['recovery_from_max'] = round(recovery_pct * 100, 2)
        
        if current_drawdown > max_drawdown * 0.5:
            score += 15
            details['recovery_status'] = 'strong_recovery'
        else:
            details['recovery_status'] = 'limited_recovery'
        
        final_score = np.clip(score, 0, 100)
        details['score_interpretation'] = self._interpret_score(final_score)
        return final_score, details
    
    def _analyze_market_context(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze overall market context and conditions."""
        context = {}
        
        if len(df) < 20:
            return {'status': 'insufficient_data'}
        
        current_price = df['close'].iloc[-1]
        
        # Support/Resistance levels (recent highs/lows)
        recent_high = df['high'].tail(30).max()
        recent_low = df['low'].tail(30).min()
        
        context['current_price'] = round(current_price, 2)
        context['recent_high_30d'] = round(recent_high, 2)
        context['recent_low_30d'] = round(recent_low, 2)
        context['distance_to_high'] = round(((recent_high - current_price) / current_price) * 100, 2)
        context['distance_to_low'] = round(((current_price - recent_low) / current_price) * 100, 2)
        
        # Price position in range
        price_range = recent_high - recent_low
        if price_range > 0:
            position_in_range = (current_price - recent_low) / price_range
            context['position_in_range'] = round(position_in_range * 100, 2)
            
            if position_in_range > 0.8:
                context['range_position'] = 'near_resistance'
            elif position_in_range < 0.2:
                context['range_position'] = 'near_support'
            else:
                context['range_position'] = 'mid_range'
        
        # Volume analysis
        if 'volume' in df.columns:
            avg_volume = df['volume'].tail(20).mean()
            recent_volume = df['volume'].tail(5).mean()
            context['avg_volume_20d'] = round(avg_volume, 2)
            context['recent_volume_5d'] = round(recent_volume, 2)
            
            if recent_volume > avg_volume * 1.5:
                context['volume_signal'] = 'high_volume_breakout'
            elif recent_volume < avg_volume * 0.5:
                context['volume_signal'] = 'low_volume_consolidation'
            else:
                context['volume_signal'] = 'normal'
        
        # Volatility state
        if len(df) >= 20:
            returns = df['close'].pct_change()
            recent_vol = returns.tail(7).std()
            avg_vol = returns.tail(30).std()
            
            if recent_vol > avg_vol * 1.5:
                context['volatility_state'] = 'high_volatility'
            elif recent_vol < avg_vol * 0.7:
                context['volatility_state'] = 'low_volatility'
            else:
                context['volatility_state'] = 'normal'
        
        return context
    
    def _interpret_score(self, score: float) -> str:
        """Interpret score as text."""
        if score >= 80:
            return 'Rất tích cực'
        elif score >= 60:
            return 'Tích cực'
        elif score >= 40:
            return 'Trung lập'
        elif score >= 20:
            return 'Tiêu cực'
        else:
            return 'Rất tiêu cực'
    
    def _generate_insights(
        self,
        signal: InvestmentSignal,
        trend_details: Dict,
        technical_details: Dict,
        risk_details: Dict,
        regime_details: Dict,
        drawdown_details: Dict,
        market_context: Dict
    ) -> Dict[str, Any]:
        """Generate actionable investment insights."""
        insights = {
            'summary': '',
            'key_factors': [],
            'risks': [],
            'opportunities': [],
            'action_plan': []
        }
        
        # Generate summary
        if signal == InvestmentSignal.STRONG_BUY:
            insights['summary'] = '🚀 Tín hiệu MUA MẠNH - Nhiều yếu tố hỗ trợ xu hướng tăng'
        elif signal == InvestmentSignal.BUY:
            insights['summary'] = '📈 Tín hiệu MUA - Xu hướng tích cực chiếm ưu thế'
        elif signal == InvestmentSignal.HOLD:
            insights['summary'] = '⏸️ Tín hiệu GIỮ - Thị trường chưa rõ ràng, nên quan sát'
        elif signal == InvestmentSignal.SELL:
            insights['summary'] = '📉 Tín hiệu BÁN - Áp lực bán gia tăng'
        else:
            insights['summary'] = '🔻 Tín hiệu BÁN MẠNH - Rủi ro cao, nên thoát vị thế'
        
        # Key factors
        if trend_details.get('trend_direction') == 'uptrend':
            insights['key_factors'].append(f"✅ Xu hướng tăng: Giá tăng {abs(trend_details.get('price_change_7d_vs_30d', 0))}% trong 7 ngày")
        elif trend_details.get('trend_direction') == 'downtrend':
            insights['key_factors'].append(f"⚠️ Xu hướng giảm: Giá giảm {abs(trend_details.get('price_change_7d_vs_30d', 0))}% trong 7 ngày")
        
        if technical_details.get('rsi_signal') == 'oversold_strong_buy':
            insights['opportunities'].append(f"💡 RSI quá bán ({technical_details.get('rsi')}), cơ hội mua tốt")
        elif technical_details.get('rsi_signal') == 'overbought_strong_sell':
            insights['risks'].append(f"⚠️ RSI quá mua ({technical_details.get('rsi')}), có thể điều chỉnh")
        
        if technical_details.get('macd_crossover') == 'recent_bullish_crossover':
            insights['opportunities'].append("💡 MACD vừa cắt lên Signal - Tín hiệu mua mới")
        elif technical_details.get('macd_crossover') == 'recent_bearish_crossover':
            insights['risks'].append("⚠️ MACD vừa cắt xuống Signal - Tín hiệu bán mới")
        
        # Market context
        if market_context.get('range_position') == 'near_support':
            insights['opportunities'].append(f"💡 Giá gần vùng hỗ trợ {market_context.get('recent_low_30d')} - Điểm vào tốt")
        elif market_context.get('range_position') == 'near_resistance':
            insights['risks'].append(f"⚠️ Giá gần vùng kháng cự {market_context.get('recent_high_30d')} - Có thể gặp áp lực bán")
        
        if market_context.get('volume_signal') == 'high_volume_breakout':
            insights['opportunities'].append("💡 Khối lượng tăng mạnh - Xu hướng có thể kéo dài")
        
        # Action plan based on signal
        if signal in [InvestmentSignal.STRONG_BUY, InvestmentSignal.BUY]:
            insights['action_plan'] = [
                "1. Xem xét mở vị thế mua với quy mô phù hợp với khẩu vị rủi ro",
                f"2. Đặt stop-loss dưới vùng hỗ trợ {market_context.get('recent_low_30d', 'N/A')}",
                f"3. Mục tiêu chốt lời gần vùng kháng cự {market_context.get('recent_high_30d', 'N/A')}",
                "4. Theo dõi RSI và MACD để xác nhận xu hướng"
            ]
        elif signal == InvestmentSignal.HOLD:
            insights['action_plan'] = [
                "1. Giữ vị thế hiện tại, chờ tín hiệu rõ ràng hơn",
                "2. Theo dõi chặt các chỉ báo kỹ thuật (RSI, MACD)",
                "3. Đặt cảnh báo giá tại vùng support/resistance",
                "4. Chuẩn bị kế hoạch cho cả 2 kịch bản tăng/giảm"
            ]
        else:  # SELL or STRONG_SELL
            insights['action_plan'] = [
                "1. Xem xét chốt lời/cắt lỗ vị thế hiện có",
                f"2. Nếu giữ, đặt stop-loss chặt trên {market_context.get('recent_high_30d', 'N/A')}",
                "3. Chờ tín hiệu đảo chiều trước khi mua lại",
                "4. Ưu tiên bảo toàn vốn trong giai đoạn này"
            ]
        
        return insights
    
    def _score_to_signal(self, score: float) -> Tuple[InvestmentSignal, float]:
        """
        Convert composite score to investment signal and confidence.
        
        Returns:
            (signal, confidence_percentage)
        """
        if score >= 80:
            return InvestmentSignal.STRONG_BUY, min((score - 80) * 5, 100)
        elif score >= 60:
            return InvestmentSignal.BUY, min((score - 60) * 5, 100)
        elif score >= 40:
            return InvestmentSignal.HOLD, 100 - abs(score - 50) * 2
        elif score >= 20:
            return InvestmentSignal.SELL, min((40 - score) * 5, 100)
        else:
            return InvestmentSignal.STRONG_SELL, min((20 - score) * 5, 100)
