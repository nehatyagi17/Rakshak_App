/**
 * Machine Learning Utilities for Rakshak
 * Provides a resilient wrapper around TFLite for environments like Expo Go.
 */

// We use dynamic imports (require) for TFLite to prevent early crashes in Expo Go
let Tflite: any = null;
try {
  Tflite = require('react-native-fast-tflite');
} catch (e) {
  console.warn("⚠️ TFLite Native Module not found. Switching to Simulation Mode.");
}

export interface ModelWrapper {
  run: (inputs: any[]) => Promise<any[]>;
  isMock: boolean;
}

/**
 * Safely loads a TFLite model or returns a mock if the native module is missing.
 */
export const safeLoadModel = async (modelAsset: any, name: string): Promise<ModelWrapper> => {
  if (Tflite && Tflite.loadTensorflowModel) {
    try {
      const model = await Tflite.loadTensorflowModel(modelAsset);
      return {
        run: async (inputs: any[]) => await model.run(inputs),
        isMock: false
      };
    } catch (e) {
      console.error(`❌ Failed to load real model [${name}]:`, e);
    }
  }

  // Fallback / Simulation Mock
  console.log(`ℹ️ Initializing Mock Model for [${name}]`);
  return {
    run: async (inputs: any[]) => {
      // Simulate processing time
      await new Promise(resolve => setTimeout(resolve, 50));
      // Return a simulated high-probability output if specific conditions are met
      // For testing, we can trigger a high score occasionally
      const mockScore = Math.random() < 0.05 ? 0.92 : 0.02; 
      return [[0, mockScore]]; // Standard [label0, label1] format
    },
    isMock: true
  };
};

/**
 * Simulates a keyword trigger for testing purposes
 */
export const simulateTrigger = (onTrigger: () => void) => {
  console.warn("🚨 Simulating Keyword Detection...");
  onTrigger();
};
