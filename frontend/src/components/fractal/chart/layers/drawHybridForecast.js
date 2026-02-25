/**
 * STEP A — Hybrid Forecast Renderer
 * BLOCK 73.3 — Unified Path Integration
 * 
 * NOW uses unifiedPath as single source of truth:
 * - syntheticPath[0] = NOW (anchorPrice)
 * - syntheticPath[1..N] = forecast
 * - markers come from syntheticPath directly
 * 
 * This eliminates:
 * - 7→14 continuity breaks
 * - Marker position mismatches
 * - Anchor price discrepancies
 */

import { formatPrice as formatPriceUtil } from '../../../../utils/priceFormatter';

export function drawHybridForecast(
  ctx,
  forecast,
  primaryMatch,
  xRightAnchor,
  y,
  plotW,
  marginTop,
  marginBottom,
  canvasHeight,
  markers = [], // Legacy markers (fallback)
  symbol = 'BTC' // Asset symbol for price formatting
) {
  // BLOCK 73.3: Prefer unifiedPath if available
  const unifiedPath = forecast?.unifiedPath;
  
  let syntheticData, replayData, anchorPrice, N;
  
  if (unifiedPath?.syntheticPath?.length) {
    // NEW: Use unified path (includes t=0)
    syntheticData = unifiedPath.syntheticPath;
    replayData = unifiedPath.replayPath || [];
    anchorPrice = unifiedPath.anchorPrice;
    N = unifiedPath.horizonDays;
  } else if (forecast?.pricePath?.length) {
    // LEGACY: Fallback to old format (no t=0)
    const legacyPath = forecast.pricePath;
    anchorPrice = forecast.currentPrice;
    N = legacyPath.length;
    
    // Convert to unified format
    syntheticData = [{ t: 0, price: anchorPrice, pct: 0 }];
    for (let i = 0; i < N; i++) {
      syntheticData.push({
        t: i + 1,
        price: legacyPath[i],
        pct: ((legacyPath[i] / anchorPrice) - 1) * 100
      });
    }
    
    // Legacy replay from primaryMatch
    if (primaryMatch?.aftermathNormalized?.length) {
      replayData = [{ t: 0, price: anchorPrice, pct: 0 }];
      for (let i = 0; i < primaryMatch.aftermathNormalized.length; i++) {
        const ret = primaryMatch.aftermathNormalized[i];
        replayData.push({
          t: i + 1,
          price: anchorPrice * (1 + ret),
          pct: ret * 100
        });
      }
    } else {
      replayData = [];
    }
  } else {
    return; // No data to render
  }
  
  // Forecast zone width (increased for longer horizons like 180d/365d)
  const forecastZoneWidth = Math.min(plotW * 0.55, 420) - 50;
  const dayToX = (t) => xRightAnchor + (t / N) * forecastZoneWidth;
  
  // === 1. FORECAST ZONE BACKGROUND ===
  ctx.save();
  const bgGradient = ctx.createLinearGradient(
    xRightAnchor, 0,
    xRightAnchor + forecastZoneWidth, 0
  );
  bgGradient.addColorStop(0, "rgba(0,0,0,0.03)");
  bgGradient.addColorStop(1, "rgba(0,0,0,0.01)");
  ctx.fillStyle = bgGradient;
  ctx.fillRect(
    xRightAnchor,
    marginTop,
    forecastZoneWidth + 70,
    canvasHeight - marginTop - marginBottom
  );
  ctx.restore();
  
  // === 2. NOW SEPARATOR ===
  ctx.save();
  ctx.strokeStyle = "rgba(180, 0, 0, 0.4)";
  ctx.lineWidth = 1.5;
  ctx.setLineDash([5, 5]);
  ctx.beginPath();
  ctx.moveTo(xRightAnchor, marginTop);
  ctx.lineTo(xRightAnchor, canvasHeight - marginBottom);
  ctx.stroke();
  ctx.restore();
  
  // === 3. NOW LABEL ===
  ctx.save();
  ctx.fillStyle = "#dc2626";
  ctx.font = "bold 10px system-ui";
  ctx.textAlign = "center";
  ctx.fillText("NOW", xRightAnchor, marginTop - 6);
  ctx.restore();
  
  // === 4. SYNTHETIC LINE (green) with spline ===
  // Build points from unified path (t=0..N)
  const syntheticPoints = syntheticData.map(p => ({
    x: dayToX(p.t),
    y: y(p.price)
  }));
  
  ctx.save();
  ctx.shadowColor = 'rgba(22, 163, 74, 0.25)';
  ctx.shadowBlur = 6;
  ctx.strokeStyle = '#22c55e';
  ctx.lineWidth = 2.5;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  
  drawSpline(ctx, syntheticPoints);
  ctx.stroke();
  ctx.restore();
  
  // === 5. REPLAY LINE (purple) with spline ===
  // BLOCK 73.3: Use replayData from unified path
  if (replayData.length > 0) {
    const replayPoints = replayData.map(p => ({
      x: dayToX(p.t),
      y: y(p.price)
    }));
    
    ctx.save();
    ctx.shadowColor = 'rgba(139, 92, 246, 0.2)';
    ctx.shadowBlur = 4;
    ctx.strokeStyle = '#8b5cf6';
    ctx.lineWidth = 2;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.setLineDash([6, 4]);
    
    drawSpline(ctx, replayPoints);
    ctx.stroke();
    ctx.restore();
  }
  
  // === 5.5 TAIL RISK LINE (Worst-case 5%) ===
  // Draw the same tail risk line as in synthetic mode
  if (forecast.tailFloor && forecast.tailFloor > 0) {
    const tailY = y(forecast.tailFloor);
    const tailPrice = Math.round(forecast.tailFloor);
    // Use centralized formatter based on asset symbol
    const formattedPrice = formatPriceUtil(tailPrice, symbol, { compact: false });
    
    // Only draw if within visible range
    if (tailY > marginTop && tailY < canvasHeight - marginBottom) {
      ctx.save();
      
      // Dashed risk line
      ctx.strokeStyle = "rgba(200, 0, 0, 0.6)";
      ctx.lineWidth = 1.5;
      ctx.setLineDash([6, 5]);
      ctx.beginPath();
      ctx.moveTo(xRightAnchor, tailY);
      ctx.lineTo(dayToX(N), tailY);
      ctx.stroke();
      
      // Red dot at forecast start
      ctx.beginPath();
      ctx.arc(xRightAnchor, tailY, 4, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(200, 0, 0, 0.85)";
      ctx.fill();
      
      // Human-readable label: "Worst-case (5%): $56,636"
      ctx.fillStyle = "rgba(180, 0, 0, 0.9)";
      ctx.font = "bold 10px system-ui";
      ctx.textAlign = "left";
      ctx.fillText("Worst-case (5%):", xRightAnchor + 10, tailY - 5);
      
      // Price value - prominent
      ctx.font = "bold 11px system-ui";
      ctx.fillStyle = "rgba(180, 0, 0, 0.95)";
      ctx.fillText(formattedPrice, xRightAnchor + 112, tailY - 5);
      
      ctx.restore();
    }
  }
  
  // === 6. END MARKERS ===
  const lastSynthetic = syntheticData[syntheticData.length - 1];
  const lastSyntheticY = y(lastSynthetic.price);
  const endX = dayToX(N);
  
  // Synthetic end marker
  ctx.save();
  ctx.fillStyle = '#22c55e';
  ctx.beginPath();
  ctx.arc(endX, lastSyntheticY, 5, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = '#fff';
  ctx.beginPath();
  ctx.arc(endX, lastSyntheticY, 2.5, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
  
  // Replay end marker (BLOCK 73.3: use replayData)
  if (replayData.length > 0) {
    const lastReplay = replayData[replayData.length - 1];
    const lastReplayY = y(lastReplay.price);
    ctx.save();
    ctx.fillStyle = '#8b5cf6';
    ctx.beginPath();
    ctx.arc(endX, lastReplayY, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#fff';
    ctx.beginPath();
    ctx.arc(endX, lastReplayY, 2.5, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  }
  
  // === 7. LEGEND ===
  const legendX = xRightAnchor + 12;
  const legendY = marginTop + 20;
  
  ctx.save();
  ctx.font = "bold 10px system-ui";
  
  // Hybrid legend (was "Synthetic" - changed to "Hybrid" since this is hybrid mode)
  ctx.fillStyle = '#22c55e';
  ctx.beginPath();
  ctx.arc(legendX, legendY, 4, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = '#444';
  ctx.textAlign = 'left';
  ctx.fillText('Hybrid', legendX + 10, legendY + 3);
  
  // Replay legend
  if (replayData.length > 0) {
    ctx.fillStyle = '#8b5cf6';
    ctx.beginPath();
    ctx.arc(legendX, legendY + 16, 4, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#444';
    ctx.fillText('Replay', legendX + 10, legendY + 19);
    
    // Similarity badge
    if (primaryMatch?.similarity) {
      ctx.font = "9px system-ui";
      ctx.fillStyle = '#888';
      ctx.fillText(`(${(primaryMatch.similarity * 100).toFixed(0)}% sim)`, legendX + 50, legendY + 19);
    }
  }
  
  ctx.restore();
  
  // === 8. INTERMEDIATE HORIZON MARKERS (BLOCK 73.3 — Unified Path) ===
  // Markers now come directly from unifiedPath (single source of truth)
  const unifiedMarkers = unifiedPath?.markers || {};
  const markerKeys = Object.keys(unifiedMarkers).filter(k => {
    const m = unifiedMarkers[k];
    return m && m.t > 0 && m.t < N; // Only intermediate markers
  });
  
  // Fallback to legacy markers if no unified markers
  const legacyMarkers = markers.length > 0 
    ? markers.filter(m => (m.day || m.dayIndex + 1) < N)
    : forecast?.markers?.filter(m => (m.day || m.dayIndex + 1) < N) || [];
  
  if (markerKeys.length > 0) {
    // Use unified markers
    markerKeys.forEach(key => {
      const marker = unifiedMarkers[key];
      const mx = dayToX(marker.t);
      const my = y(marker.price);
      
      // Calculate alpha for confidence decay effect
      const progress = marker.t / N;
      const markerAlpha = 1 - progress * 0.2;
      
      // Circle marker (smaller than endpoint)
      ctx.save();
      ctx.fillStyle = `rgba(22, 163, 74, ${markerAlpha * 0.8})`;
      ctx.beginPath();
      ctx.arc(mx, my, 4, 0, Math.PI * 2);
      ctx.fill();
      
      // White inner circle
      ctx.fillStyle = "#fff";
      ctx.beginPath();
      ctx.arc(mx, my, 2, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
      
      // Horizon label
      ctx.save();
      ctx.fillStyle = `rgba(0, 0, 0, ${0.4 + markerAlpha * 0.2})`;
      ctx.font = "bold 9px system-ui";
      ctx.textAlign = "center";
      ctx.fillText(marker.horizon, mx, my - 10);
      ctx.restore();
    });
  } else {
    // Fallback to legacy markers
    legacyMarkers.forEach(marker => {
      const day = marker.day || (marker.dayIndex + 1);
      const price = marker.price || syntheticData[day]?.price;
      if (!price || day >= N) return;
      
      const mx = dayToX(day);
      const my = y(price);
      
      // Calculate alpha for confidence decay effect
      const progress = day / N;
      const markerAlpha = 1 - progress * 0.2;
      
      // Circle marker (smaller than endpoint)
      ctx.save();
      ctx.fillStyle = `rgba(22, 163, 74, ${markerAlpha * 0.8})`;
      ctx.beginPath();
      ctx.arc(mx, my, 4, 0, Math.PI * 2);
      ctx.fill();
      
      // White inner circle
      ctx.fillStyle = "#fff";
      ctx.beginPath();
      ctx.arc(mx, my, 2, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
      
      // Horizon label
      const label = marker.horizon || `${day}d`;
      ctx.save();
      ctx.fillStyle = `rgba(0, 0, 0, ${0.4 + markerAlpha * 0.2})`;
      ctx.font = "bold 9px system-ui";
      ctx.textAlign = "center";
      ctx.fillText(label, mx, my - 10);
      ctx.restore();
    });
  }
  
  // === 9. ENDPOINT HORIZON LABEL ===
  ctx.save();
  ctx.font = "bold 10px system-ui";
  ctx.fillStyle = "rgba(0,0,0,0.5)";
  ctx.textAlign = "center";
  ctx.fillText(`${N}d`, endX, lastSyntheticY - 12);
  ctx.restore();
  
  // === 10. FORECAST SUMMARY (like in synthetic mode) ===
  // Calculate expected return from synthetic path
  const startPrice = syntheticData[0]?.price || anchorPrice;
  const endPrice = syntheticData[syntheticData.length - 1]?.price || startPrice;
  const expectedReturn = ((endPrice - startPrice) / startPrice) * 100;
  const sign = expectedReturn >= 0 ? '+' : '';
  
  // Draw Forecast summary at bottom
  ctx.save();
  ctx.font = "11px system-ui";
  ctx.textAlign = "left";
  
  const labelX = xRightAnchor + 10;
  const labelY = canvasHeight - marginBottom + 18;
  
  ctx.fillStyle = "rgba(0,0,0,0.6)";
  ctx.fillText(`Forecast: ${sign}${expectedReturn.toFixed(1)}%`, labelX, labelY);
  ctx.restore();
}

// Helper: Catmull-Rom spline
function drawSpline(ctx, points) {
  if (points.length < 2) return;
  
  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);
  
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i - 1] || points[i];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[i + 2] || p2;
    
    const cp1x = p1.x + (p2.x - p0.x) / 6;
    const cp1y = p1.y + (p2.y - p0.y) / 6;
    const cp2x = p2.x - (p3.x - p1.x) / 6;
    const cp2y = p2.y - (p3.y - p1.y) / 6;
    
    ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, p2.x, p2.y);
  }
}
