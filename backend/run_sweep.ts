import { SimEntropySweepService } from './src/modules/fractal/sim/sim.entropy-sweep.service.js';
import * as fs from 'fs';

async function main() {
  console.log('Starting entropy sweep...');
  const sweep = new SimEntropySweepService();
  
  const result = await sweep.run({
    from: '2020-01-01',
    to: '2024-01-01',
    iterations: 300,
    blockSizes: [5],
    warn: [0.50, 0.60],
    hard: [0.70, 0.80],
    minScale: [0.25],
    emaAlpha: [0.20],
    minTrades: 8,
    minSharpe: 0.2,
  });
  
  fs.writeFileSync('/tmp/sweep_result.json', JSON.stringify(result, null, 2));
  console.log('Result saved to /tmp/sweep_result.json');
  console.log('Best candidate:', result.best?.params);
  console.log('Best P95DD:', result.best?.mc?.p95MaxDD);
}

main().catch(e => {
  console.error('Error:', e);
  process.exit(1);
});
