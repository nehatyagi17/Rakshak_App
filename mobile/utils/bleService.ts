import { NativeModules, NativeEventEmitter, Platform } from 'react-native';

// --- MOCK TRANSITION FOR EXPO GO ---
// Because react-native-ble-manager is a native module, 
// we mock it here so the app can still bundle and run in Expo Go [Simulation Mode].
let BleManager: any;
try {
  BleManager = require('react-native-ble-manager').default;
} catch (e) {
  console.log("⚠️ BLE Native Module not found. Switching Handshake to Simulation Mode.");
  BleManager = {
    start: async () => {},
    scan: async () => {},
    stopScan: async () => {},
  };
}

const BleManagerModule = NativeModules.BleManager;
const bleManagerEmitter = BleManagerModule ? new NativeEventEmitter(BleManagerModule) : null;

export class HandshakeService {
  private static instance: HandshakeService;
  private isScanning = false;
  private targetToken: string | null = null;
  private onProximityMatch: (token: string) => void = () => {};

  private constructor() {
    BleManager.start({ showAlert: false }).catch(() => {});
  }

  public static getInstance(): HandshakeService {
    if (!HandshakeService.instance) {
      HandshakeService.instance = new HandshakeService();
    }
    return HandshakeService.instance;
  }

  /**
   * VICTIM SIDE: Start advertising the emergency token.
   */
  public async startAdvertising(token: string) {
    console.log(`📡 [SIMULATED] BLE Broadcast for token: ${token}`);
    // In Simulation Mode, we just log the broadcast.
  }

  /**
   * VOLUNTEER SIDE: Start scanning for a specific SOS token.
   */
  public startScanning(token: string, onMatch: (foundToken: string) => void) {
    if (this.isScanning) return;
    
    this.targetToken = token.trim().toLowerCase();
    this.onProximityMatch = onMatch;
    this.isScanning = true;

    console.log(`🔍 [SIMULATED] Scanning for proximity to token: ${this.targetToken}`);

    // In Simulation Mode, we automatically match after 10 seconds 
    // to simulate the time it takes to reach the victim.
    setTimeout(() => {
      if (this.isScanning) {
        console.warn(`🤝 [SIMULATED] PROXIMITY HANDSHAKE DETECTED!`);
        this.stopScanning();
        this.onProximityMatch(this.targetToken!);
      }
    }, 10000); 
  }

  public stopScanning() {
    this.isScanning = false;
    BleManager.stopScan().catch(() => {});
  }
}

export const handshakeService = HandshakeService.getInstance();
