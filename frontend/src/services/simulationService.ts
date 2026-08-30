import api from './api'
import type { SimulationScenario, SimulationResult } from '../types'

export const simulationService = {
  listScenarios: (): Promise<SimulationScenario[]> =>
    api.get('/simulation/scenarios').then(r => r.data),

  runScenario: (scenarioId: string): Promise<SimulationResult> =>
    api.post(`/simulation/run/${scenarioId}`).then(r => r.data),

  runAll: (): Promise<SimulationResult[]> =>
    api.post('/simulation/run-all').then(r => r.data),
}
