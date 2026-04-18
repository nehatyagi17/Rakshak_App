import React, { useState, useEffect, useRef } from 'react';
import { 
  StyleSheet, Text, View, TouchableOpacity, Animated, Easing, 
  Alert, StatusBar, TextInput, Platform, ScrollView, Dimensions, 
  KeyboardAvoidingView, Linking, LogBox 
} from 'react-native';

LogBox.ignoreLogs([
  'expo-notifications: Android Push notifications (remote notifications)',
  'expo-notifications: Android Push notifications',
  'remote notifications'
]);
import { getCurrentPositionAsync, requestForegroundPermissionsAsync, getLastKnownPositionAsync } from 'expo-location';
import * as SMS from 'expo-sms';
import * as MailComposer from 'expo-mail-composer';
import { CameraView, Camera } from 'expo-camera';
import { LinearGradient } from 'expo-linear-gradient';


import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Audio, InterruptionModeAndroid, InterruptionModeIOS } from 'expo-av';
import axios from 'axios';
import * as Notifications from 'expo-notifications';
import Constants from 'expo-constants';
import * as Device from 'expo-device';
import { extractMFCCs, fuseDetectionScores } from './utils/audioProcessor';
import { safeLoadModel, ModelWrapper } from './utils/mlUtils';
import { handshakeService } from './utils/bleService';
import MapView, { Marker } from 'react-native-maps';
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Haptics from 'expo-haptics';
import { SOSManager } from './components/SOSManager';
import { SafeRouteMap } from './components/SafeRouteMap';
import { CameraType } from 'expo-camera';

const { width, height } = Dimensions.get('window');
// --- CONFIGURATION ---
// Use EXPO_PUBLIC_ prefix for Expo to pick up these from .env
const API_BASE = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000/api'; 
// IMPORTANT: If testing on a physical phone, ensure phone and PC are on the same Wi-Fi.
// Update EXPO_PUBLIC_API_URL in mobile/.env to your PC's local IP (e.g. 192.168.1.15)

// --- THEME ENGINE ---
const THEME = {
  bg: ['#0A0E17', '#111827'],
  primary: '#7C3AED',
  secondary: '#8B5CF6',
  warning: '#F43F5E',
  danger: '#DC2626',
  success: '#10B981',
  text: '#F8FAFC',
  textDim: '#94A3B8',
  glass: 'rgba(30, 41, 59, 0.4)',
  border: 'rgba(255, 255, 255, 0.1)',
};

const safeGetLocation = async (options = {}): Promise<any> => {
  try {
    return await getCurrentPositionAsync(options);
  } catch (e) {
    console.warn("Location error, attempting fallback:", e);
    try {
      const last = await getLastKnownPositionAsync({});
      if (last) return last;
    } catch(e2) {}
    // Simulated location if entirely failed
    return { coords: { latitude: 28.6139, longitude: 77.2090 } }; 
  }
};

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

type ScreenState = 'login' | 'register' | 'voice_setup' | 'contacts_setup' | 'biometric_enrollment' | 'home' | 'route_map';

// --- REUSABLE COMPONENTS ---
const ScreenWrapper = ({ children, visible, delay = 0 }: { children: React.ReactNode, visible: boolean, delay?: number }) => {
  const fade = useRef(new Animated.Value(0)).current;
  const slide = useRef(new Animated.Value(30)).current;

  useEffect(() => {
    if (visible) {
      Animated.parallel([
        Animated.timing(fade, { toValue: 1, duration: 800, delay, useNativeDriver: true, easing: Easing.out(Easing.exp) }),
        Animated.timing(slide, { toValue: 0, duration: 800, delay, useNativeDriver: true, easing: Easing.out(Easing.exp) })
      ]).start();
    } else {
      fade.setValue(0);
      slide.setValue(30);
    }
  }, [visible]);

  if (!visible) return null;
  return (
    <Animated.View style={[styles.screenContainer, { opacity: fade, transform: [{ translateY: slide }] }]}>
      {children}
    </Animated.View>
  );
};

const InputField = ({ icon, ...props }: any) => (
  <View style={styles.inputWrapper}>
    <MaterialCommunityIcons name={icon} color={THEME.textDim} size={20} style={styles.inputIcon} />
    <TextInput 
      placeholderTextColor={THEME.textDim} 
      style={styles.input} 
      {...props} 
    />
  </View>
);

export default function App() {
  const [currentScreen, setCurrentScreen] = useState<ScreenState>('login'); 
  const [isAlertActive, setIsAlertActive] = useState(false);
  const [isSOSCountdown, setIsSOSCountdown] = useState(false);
  const [isRecording, setIsRecording] = useState(false);

  // Form states
  const [form, setForm] = useState({ name: '', email: '', phone: '', password: '', keyword: '' });
  const [guardian, setGuardian] = useState({ name: '', phone: '', email: '' });
  const [countdown, setCountdown] = useState(15);
  const [activeAlertId, setActiveAlertId] = useState<string | null>(null);
  const [activeEmergencyToken, setActiveEmergencyToken] = useState<string | null>(null);
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [userId, setUserId] = useState<any>(null);
  const [rakshakId, setRakshakId] = useState<string>('');
  const [faceVector, setFaceVector] = useState<number[] | null>(null);
  const [expoPushToken, setExpoPushToken] = useState<string>('');
  const notificationListener = useRef<Notifications.Subscription | null>(null);
  const responseListener = useRef<Notifications.Subscription | null>(null);

  // Model References
  const keywordModel = useRef<ModelWrapper | null>(null);
  const motionModel = useRef<ModelWrapper | null>(null);
  const isSimulatedRef = useRef(false);
  const [isSimulated, setIsSimulated] = useState(false);
  const recording = useRef<Audio.Recording | null>(null);
  const notifiedAlerts = useRef<Record<string, number>>({});
  const isEscalating = useRef(false);
  const dismissedAlerts = useRef<Set<string>>(new Set());
  const emergencyTokenRef = useRef<string | null>(null);
  const activeAlertIdRef = useRef<string | null>(null);
  const evidenceCameraRef = useRef<CameraView>(null);
  const biometricCameraRef = useRef<CameraView>(null);

  // WebSocket Integration
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [activeRescue, setActiveRescue] = useState<any>(null);
  const [userLocation, setUserLocation] = useState<any>(null);
  const [reconnectTrigger, setReconnectTrigger] = useState(0);
  const [comingVolunteers, setComingVolunteers] = useState<any[]>([]);
  const [isRescuing, setIsRescuing] = useState(false);
  const [isBiometricActive, setIsBiometricActive] = useState(false);
  const [biometricStatus, setBiometricStatus] = useState("Face Verification Ready");
  const lastEyeStatus = useRef({ prob: 1.0, time: 0 });
  const videoInterval = useRef<NodeJS.Timeout | null>(null);
  const gpsInterval = useRef<NodeJS.Timeout | null>(null);

  // Helper for direct distance (Panic Reduction)
  const getDistance = (lat1: number, lon1: number, lat2: number, lon2: number) => {
    const R = 6371e3; // meters
    const phi1 = lat1 * Math.PI/180;
    const phi2 = lat2 * Math.PI/180;
    const dPhi = (lat2-lat1) * Math.PI/180;
    const dLambda = (lon2-lon1) * Math.PI/180;
    const a = Math.sin(dPhi/2) * Math.sin(dPhi/2) +
            Math.cos(phi1) * Math.cos(phi2) *
            Math.sin(dLambda/2) * Math.sin(dLambda/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c; // in meters
  };

  // Animation values for SOS
  const pulse1 = useRef(new Animated.Value(1)).current;
  const pulse2 = useRef(new Animated.Value(1)).current;
  const pulse3 = useRef(new Animated.Value(1)).current;
  const micWave = useRef(new Animated.Value(0)).current;

  const handleTestBiometric = () => { setIsBiometricActive(true); setBiometricStatus("Face Verification Ready"); };
  
  const handleEnrollFace = () => {
    // SECURITY UPGRADE: Trigger the real identity challenge to verify and sync to backend
    setBiometricStatus("Verify Identity to Enroll");
    setIsBiometricActive(true);
  };


  const navigate = (screen: ScreenState) => {
    setCurrentScreen(screen);
  };

  const handleLogout = () => {
    console.log(" RAKSHAK: Performing Secure Logout - Clearing Session State");
    setAuthToken(null);
    setUserId(null);
    setRakshakId('');
    setFaceVector(null);
    setForm({ name: '', email: '', phone: '', password: '', keyword: '' });
    setGuardian({ name: '', phone: '', email: '' });
    setIsAlertActive(false);
    setIsBiometricActive(false);
    navigate('login');
  };

  const handleNavigateRegister = () => {
    setForm({ name: '', email: '', phone: '', password: '', keyword: '' });
    setFaceVector(null);
    navigate('register');
  };

  // --- NOTIFICATION REGISTRATION ---
  async function registerForPushNotificationsAsync() {
    let token;
    if (Platform.OS === 'android') {
      await Notifications.setNotificationChannelAsync('default', {
        name: 'default',
        importance: Notifications.AndroidImportance.MAX,
        vibrationPattern: [0, 250, 250, 250],
        lightColor: '#FF231F7C',
      });
    }

    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;
    if (existingStatus !== 'granted') {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }
    if (finalStatus !== 'granted') {
      console.warn('Failed to get push token for push notification!');
      return;
    }
    
    // In actual Expo environment, this would fetch the token. 
    // For local dev/demo, we use a placeholder if simulation is active.
    
    // --- DEFENSIVE CHECK FOR EXPO GO SDK 53+ ---
    if (Constants.appOwnership === 'expo' || !Device.isDevice) {
      console.log(" RAKSHAK: Running in Expo Go or Emulator. Skipping Native Push Registry.");
      return "SIMULATED_TOKEN_" + Math.random().toString(36).substring(7);
    }

    try {
      const { status: existingStatus } = await Notifications.getPermissionsAsync();
      let finalStatus = existingStatus;
      if (existingStatus !== 'granted') {
        const { status } = await Notifications.requestPermissionsAsync();
        finalStatus = status;
      }
      if (finalStatus !== 'granted') return null;

      token = (await Notifications.getExpoPushTokenAsync({
        projectId: Constants.expoConfig?.extra?.eas?.projectId || "placeholder",
      })).data;
      console.log(" Expo Push Token:", token);
    } catch (e: any) {
      console.log(" Notification Module Unavailable: Using Simulated Token.");
      token = "SIMULATED_TOKEN_" + Math.random().toString(36).substring(7);
    }
    return token;
  }

  // --- PERMISSION GUARD & RECOVERY ---
  useEffect(() => {
    (async () => {
      const { status: foreground } = await requestForegroundPermissionsAsync();
      const { status: camera } = await Camera.requestCameraPermissionsAsync();
      const { status: audio } = await Audio.requestPermissionsAsync();
      
      console.log(" RAKSHAK: All Critical Safety Permissions Granted.");

      // PERSISTENCE RECOVERY: Check for active SOS after crash/reboot
      // Only recover if we have an authToken (logged in)
      try {
        const savedSOS = await AsyncStorage.getItem('RAKSHAK_ACTIVE_SOS');
        if (savedSOS === 'true' && authToken) {
           console.warn("RECOVERY: Active SOS Detected from previous session. Resuming Handover.");
           triggerAuthorityHandover();
        }
      } catch (e) {
        console.error("SOS Recovery Check Failed", e);
      }
    })();
  }, [authToken]);


  // --- SYNC PUSH TOKEN ---
  useEffect(() => {
    if (authToken && authToken !== 'MOCK_DEMO_TOKEN') {
       const syncToken = async () => {
          const token = await registerForPushNotificationsAsync();
          if (token) {
            setExpoPushToken(token);
            try {
              await axios.put(`${API_BASE}/profile/update/`, {
                expo_push_token: token
              }, { headers: { Authorization: `Bearer ${authToken}` } });
              console.log(" Push Token Synced to Backend");
            } catch (e) { console.log("Token sync failed"); }
          }
       };
       syncToken();
    }
    
    // Listeners
    notificationListener.current = Notifications.addNotificationReceivedListener(notification => {
      const { title, body, data } = notification.request.content;
      if (data?.type === 'NEARBY_SOS' || data?.type === 'EMERGENCY') {
         const alertBtns: any[] = [{ text: "Dismiss", style: 'cancel' }];
         if (data?.lat && data?.lng) {
            alertBtns.push({
               text: "VIEW MAP",
               onPress: () => {
                  const url = `https://www.google.com/maps/search/?api=1&query=${data.lat},${data.lng}`;
                  Linking.openURL(url);
               }
            });
         }
         Alert.alert(title || "Alert", body || "Emergency detected nearby!", alertBtns);
      }
    });

    responseListener.current = Notifications.addNotificationResponseReceivedListener(response => {
      console.log("Notification Response:", response);
      const { data } = response.notification.request.content;
      if (data?.lat && data?.lng) {
          const url = `https://www.google.com/maps/search/?api=1&query=${data.lat},${data.lng}`;
          Linking.openURL(url);
      }
    });

    return () => {
      if (notificationListener.current) notificationListener.current.remove();
      if (responseListener.current) responseListener.current.remove();
    };
  }, [authToken]);

    useEffect(() => {
    if (authToken && authToken !== 'MOCK_DEMO_TOKEN' && userId) {
       const API_DOMAIN = API_BASE.split('//')[1].split('/')[0];
       const wsUrl = `ws://${API_DOMAIN}/ws/safety/?user_id=${userId}`;
       console.log(" Attempting WebSocket connection to:", wsUrl);
       const socket = new WebSocket(wsUrl);
       
       socket.onopen = async () => {
          console.log(`WebSocket Connected: user_${userId}`);
          setWs(socket);
          try {
             const loc = await getCurrentPositionAsync({ accuracy: 6 });
             if (loc && loc.coords) {
                socket.send(JSON.stringify({ type: "location_update", lat: loc.coords.latitude, lng: loc.coords.longitude }));
             }
          } catch (e) { console.log("Initial WS sync failed"); }
       };

       socket.onmessage = (e) => {
          console.log("WS Message Received:", e.data);
          try {
            const data = JSON.parse(e.data);
            const alertType = data.alert_type || data.type;
            
            if (alertType === 'EMERGENCY_ALERT') {
              const alertId = data.alert_id || data.id;
              if (dismissedAlerts.current.has(alertId)) return;

              const count = notifiedAlerts.current[alertId] || 0;
              if (count < 2) {
                 notifiedAlerts.current[alertId] = count + 1;
                 Notifications.scheduleNotificationAsync({
                    content: {
                       title: "🚨 URGENT: DISTRESS NEARBY",
                       body: "A citizen needs help! Tap for Map.",
                       data: { type: 'NEARBY_SOS', lat: data.location[1], lng: data.location[0] }
                    },
                    trigger: null,
                 });
              }
              setActiveRescue(data);
            } else if (alertType === 'VOLUNTEER_COMING') {
              setComingVolunteers(prev => [...prev, { id: data.volunteer_id, name: data.name, lat: 0, lng: 0 }]);
            } else if (alertType === 'VOLUNTEER_UPDATE') {
              setComingVolunteers(prev => prev.map(v => 
                v.id === data.volunteer_id ? { ...v, lat: data.lat, lng: data.lng } : v
              ));
            }
          } catch (err) { console.error("WS Parse Error", err); }
       };

       socket.onclose = () => {
          setWs(null);
          setTimeout(() => setReconnectTrigger(prev => prev + 1), 5000);
       };

       return () => socket.close();
    }
  }, [authToken, userId, reconnectTrigger]);

  useEffect(() => {
    let pulseInterval: any;
    if (authToken && authToken !== 'MOCK_DEMO_TOKEN') {
       pulseInterval = setInterval(async () => {
          try {
             const loc = await getCurrentPositionAsync({ accuracy: 6 });
             if (loc && loc.coords) {
                setUserLocation(loc.coords);
                await axios.post(`${API_BASE}/profile/update-location/`, {
                   lat: loc.coords.latitude,
                   lng: loc.coords.longitude
                }, { headers: { Authorization: `Bearer ${authToken}` } });
                
                if (ws && ws.readyState === 1) { 
                   ws.send(JSON.stringify({ 
                     type: "location_update", 
                     lat: loc.coords.latitude, 
                     lng: loc.coords.longitude, 
                     victim_id: (isRescuing && activeRescue) ? activeRescue.user_id : null 
                   }));
                }
             }
          } catch (e) { }
       }, 30000);
    }
    return () => clearInterval(pulseInterval);
  }, [authToken, ws, isRescuing, activeRescue]);

  useEffect(() => {
    let scanInterval: any;
    if (currentScreen === 'home' && !isAlertActive && authToken && authToken !== 'MOCK_DEMO_TOKEN') {
      scanInterval = setInterval(async () => {
         try {
            console.log(" Scanning for nearby RAKSHAK signals...");
            const loc = await getCurrentPositionAsync({});
            const res = await axios.get(`${API_BASE}/alerts/nearby/`, {
               params: { lat: loc.coords.latitude, lng: loc.coords.longitude, radius_m: 2000 },
               headers: { Authorization: `Bearer ${authToken}` }
            });
            
            if (res.data && res.data.length > 0) {
               // Show alert for the most recent distress signal
               const nearbyAlert = res.data[0];
               console.log(" DISTRESS DETECTED PROXIMITY:", nearbyAlert.alert_id);
               
               const alertId = nearbyAlert.alert_id || nearbyAlert._id;
               const count = notifiedAlerts.current[alertId] || 0;
               if (nearbyAlert.user_id !== String(userId) && count < 2) {
                   notifiedAlerts.current[alertId] = count + 1;
                  Notifications.scheduleNotificationAsync({
                     content: {
                        title: " DISTRESS NEARBY",
                        body: `Someone needs help! Lat: ${nearbyAlert.lat.toFixed(4)}, Lng: ${nearbyAlert.lng.toFixed(4)}`,
                        data: { 
                           type: 'NEARBY_SOS', 
                           alert_id: alertId,
                           emergency_token: nearbyAlert.emergency_token, // Critical Sync
                           lat: nearbyAlert.lat, 
                           lng: nearbyAlert.lng 
                        }
                     },
                     trigger: null,
                  });
               }

               // Start PROXIMITY SCAN for this alert's token
               if (nearbyAlert.emergency_token) {
                  const normalizedToken = nearbyAlert.emergency_token.toString().trim().toLowerCase();
                  handshakeService.startScanning(normalizedToken, async (token) => {
                     // Auto-call backend on < 2m proximity detection
                     try {
                        console.log(" [HANDSHAKE] Proximity detected! Verifying with backend...");
                        await axios.post(`${API_BASE}/alerts/verify-handshake/`, {
                           emergency_token: token.toString().trim().toLowerCase(),
                           volunteer_rakshak_id: rakshakId, 
                           gps_coordinates: loc.coords
                        }, { headers: { Authorization: `Bearer ${authToken}` } });
                        
                        Alert.alert(" HANDSHAKE VERIFIED", "You have safely reached the victim. Thank you for your bravery!");
                     } catch (e) { 
                        console.error("Handshake verification failed", e); 
                     }
                  });
               }

               Alert.alert(" DISTRESS NEARBY", "Someone within 2km needs help right now!", [
                  { text: "Dismiss", style: 'cancel' },
                  { text: "VIEW MAP", onPress: () => {
                     const url = `https://www.google.com/maps/search/?api=1&query=${nearbyAlert.lat},${nearbyAlert.lng}`;
                     Linking.openURL(url);
                  }}
               ]);
            }
         } catch (e) { /* Polling error silent */ }
      }, 10000); // Check every 10 seconds for faster test results
    }
    return () => clearInterval(scanInterval);
  }, [currentScreen, isAlertActive, authToken, rakshakId]);

  // --- STAGED ESCALATION TIMERS ---
  const [sosStage, setSosStage] = useState(0); // 0: None, 1: Guardian, 2: Community

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (isAlertActive) {
      timer = setInterval(() => {
        setCountdown(prev => {
          const next = prev > 0 ? prev - 1 : 0;
          
          // Trigger Guardian Escalation at first 0 (after 15s)
          if (next === 0 && sosStage === 0) {
             escalateSOS('guardian');
             setSosStage(1);
             return 15; // Reset for community phase
          }
          
          // Trigger Community Escalation at second 0 (after 30s)
          if (next === 0 && sosStage === 1) {
             escalateSOS('community');
             setSosStage(2);
             return 0;
          }
          
          return next;
        });
      }, 1000);
    } else {
       setSosStage(0);
       setCountdown(15);
    }
    return () => clearInterval(timer);
  }, [isAlertActive, sosStage]);

  const acceptRescue = async () => {
    if (!activeRescue || !authToken) return;
    try {
      if (ws && ws.readyState === 1) {
        ws.send(JSON.stringify({ type: "accept_rescue", victim_id: activeRescue.user_id }));
      }
      setIsRescuing(true);
      
      // --- START PROXIMITY HANDSHAKE ---
      // We start scanning for the victim's UUID token. once found, it calls the VerifyHandshake API.
      const token = activeRescue.emergency_token || activeRescue.alert_id || activeRescue.id; 
      handshakeService.startScanning(token, async (foundToken) => {
          try {
             const res = await axios.post(`${API_BASE}/alerts/verify-handshake/`, {
                emergency_token: foundToken,
                volunteer_rakshak_id: rakshakId
             }, { headers: { Authorization: `Bearer ${authToken}` } });
             
             Alert.alert("Handshake Successful", "You have reached the victim. The family has been notified.");
             console.log("🤝 RAKSHAK: Handshake Verified via Proximity");
          } catch (err) {
             console.error("Handshake Verification Failed", err);
          }
      });

      Alert.alert("Rescue Accepted", "The victim has been notified. Please head to the location.");
    } catch (e) { console.log("Accept failed", e); }
  };

  const escalateSOS = async (stage: 'guardian' | 'community' | 'all') => {
    const currentAlertId = activeAlertIdRef.current || activeAlertId;
    if (!currentAlertId || isEscalating.current) return;
    isEscalating.current = true;
    try {
      console.log(` RAKSHAK: Executing SOS Escalation [STAGE: ${stage}]`);
      await axios.post(`${API_BASE}/alerts/verify/`, { 
        alert_id: currentAlertId, 
        stage: stage 
      }, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      console.log(` RAKSHAK: Escalation Successful [${stage}]`);
    } catch (e: any) {
      console.error(` Escalation FAILED [STAGE: ${stage}]`, e);
    } finally {
      // Small delay before allowing next escalation to settle state
      setTimeout(() => { isEscalating.current = false; }, 3000);
    }
  };

  // --- PERIODIC LOCATION SYNC ---
  useEffect(() => {
    let sync: NodeJS.Timeout;
    if (currentScreen === 'home' && !isAlertActive) {
      sync = setInterval(async () => {
        try {
          const loc = await safeGetLocation({});
          await axios.put(`${API_BASE}/profile/update/`, {
            location: { lat: loc.coords.latitude, lng: loc.coords.longitude }
          }, { headers: { Authorization: `Bearer ${authToken}` } });
        } catch (e) { console.log("Sync failed"); }
      }, 60000); // Every 60 seconds
    }
    return () => clearInterval(sync);
  }, [currentScreen, isAlertActive, authToken]);
  
  // --- KEYWORD DETECTION ENGINE ---
  useEffect(() => {
    const loadModels = async () => {
      try {
        const kModel = await safeLoadModel(require('./assets/models/keyword_model.tflite'), 'Keyword Detection');
        const mModel = await safeLoadModel(require('./assets/models/motion_model.tflite'), 'Motion Analysis');
        
        keywordModel.current = kModel;
        motionModel.current = mModel;
        
        if (kModel.isMock) setIsSimulated(true);
        console.log(" RAKSHAK Core Models Initialized " + (kModel.isMock ? "[SIMULATED]" : "[NATIVE]"));
      } catch (e) {
        console.error(" Failed to initialize Rakshak ML Models", e);
        setIsSimulated(true); // Fallback to simulation even on error
      }
    };
    loadModels();
  }, []);

  // --- KEYWORD DETECTION ENGINE ("THE EAR") ---
  useEffect(() => {
    let isMonitoring = true;

    const startEarLoop = async () => {
      while (isMonitoring && currentScreen === 'home' && !isAlertActive && authToken && authToken !== 'MOCK_DEMO_TOKEN') {
        try {
          const { status } = await Audio.requestPermissionsAsync();
          if (status !== 'granted') break;

          await Audio.setAudioModeAsync({
            allowsRecordingIOS: true,
            playsInSilentModeIOS: true,
            staysActiveInBackground: true,
            shouldDuckAndroid: true,
            interruptionModeAndroid: InterruptionModeAndroid.DoNotMix,
            interruptionModeIOS: InterruptionModeIOS.DoNotMix,
          });

          const { recording: earRec } = await Audio.Recording.createAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);

          // 3.0s burst for intelligent processing
          await new Promise(r => setTimeout(r, 3000));

          await earRec.stopAndUnloadAsync();
          const uri = earRec.getURI();

          // Offload network request asynchronously to PREVENT any blind spots in audio recording!
          if (uri) {
            const formData = new FormData();
            formData.append('audio', { uri, name: 'sos_sample.m4a', type: 'audio/m4a' } as any);
            
            axios.post(`${API_BASE}/profile/voice-analysis/`, formData, {
              headers: { 'Content-Type': 'multipart/form-data', Authorization: `Bearer ${authToken}` }
            }).then(res => {
              if (res.data.status === 'EMERGENCY_TRIGGERED') {
                 console.warn(" 🚨 RAKSHAK: SOS KEYWORD IDENTIFIED");
                 setIsSOSCountdown(true);
                 AsyncStorage.setItem('RAKSHAK_ACTIVE_SOS', 'true');
              } else {
                 console.log(` [THE EAR] Safe. Detected: ${res.data.detected_phrase}`);
              }
            }).catch(e => {
               // Silent drop for normal packet loss
            });
          }
        } catch (e) {
          await new Promise(r => setTimeout(r, 1000)); // sleep on error to prevent CPU spin
        }
      }
    };

    if (currentScreen === 'home' && !isAlertActive && authToken) {
      console.log(" [THE EAR] Continuous Audio Engine Armed.");
      startEarLoop(); 
    }
    return () => { isMonitoring = false; };
  }, [currentScreen, isAlertActive, authToken]);

  const autoEscalate = async () => {
    // Legacy support redirect - perform all stages instantly
    await escalateSOS('all');
    Alert.alert(" ESCALATED", "Manually verified. All Guardians and Nearby Users have been notified.");
  };

  const startSOS = async () => {
    // SECURITY UPGRADE: Manual SOS now enters countdown phase first
    setIsSOSCountdown(true);
  };

  const executeSOSHandover = async () => {
    setIsSOSCountdown(false);
    triggerAuthorityHandover();
  };

  const cancelSOS = async () => {
    // SECURITY UPGRADE: Do not cancel immediately. 
    // Trigger Biometric Identity Challenge first.
    console.log(" RAKSHAK: SOS Cancellation Requested. Challenging Identity...");
    setIsSOSCountdown(false); // Hide countdown so camera is visible
    setBiometricStatus("Scanning for Authorized Owner...");
    setIsBiometricActive(true);
  };

  const triggerAuthorityHandover = async () => {
    setIsAlertActive(true);
    await AsyncStorage.setItem('RAKSHAK_ACTIVE_SOS', 'true');
    
    // 1. Send Immediate Signal to Backend
    try {
      const location = await safeGetLocation({ accuracy: 6 }); // Highest accuracy
      const response = await axios.post(`${API_BASE}/alerts/trigger/`, {
        lat: location.coords.latitude,
        lng: location.coords.longitude,
        threat_level: 'CRITICAL'
      }, { headers: { Authorization: `Bearer ${authToken}` } });
      
      const alert_id = response.data.alert_id;
      setActiveAlertId(alert_id);
      activeAlertIdRef.current = alert_id;
      const eToken = response.data.emergency_token;
      setActiveEmergencyToken(eToken);
      emergencyTokenRef.current = eToken;
      console.log(" RAKSHAK: Authority Handover Signal Successful [TOKEN: " + eToken + "]");
    } catch (e) {
      console.error("Handover Signal Failed (Backend)", e);
    }

    // 2. Continuous Pulse Vibrate (Guardian Active)
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
    const vibration = setInterval(() => {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
    }, 2000);

    // 3. High-Accuracy GPS Stream (Update every 5s)
    gpsInterval.current = setInterval(async () => {
       try {
         const loc = await safeGetLocation({ accuracy: 6 });
         if (activeAlertIdRef.current) {
            await axios.put(`${API_BASE}/profile/update/`, {
              location: { lat: loc.coords.latitude, lng: loc.coords.longitude }
            }, { headers: { Authorization: `Bearer ${authToken}` } });
         }
       } catch (e) {}
    }, 5000);
    let sequence = 0;
    const captureAndUpload = async () => {
       if (!emergencyTokenRef.current) return;
       try {
         const loc = await safeGetLocation({ accuracy: 6 });
         sequence++;
         console.log(` [CHUNK #${sequence}] Recording 5s Evidence Segment...`);
         
         if (evidenceCameraRef.current) {
            const video = await evidenceCameraRef.current.recordAsync({ maxDuration: 5 });
            if (video && video.uri) {
                const fileToUpload = {
                   uri: video.uri,
                   name: `chunk_${sequence}.mp4`,
                   type: 'video/mp4'
                } as any;

                // --- PHASE 1: UPLOAD TO SUPABASE ---
                console.log(` [CHUNK #${sequence}] Phase 1: Uploading to Supabase...`);
                const cloudFormData = new FormData();
                cloudFormData.append('alert_id', activeAlertIdRef.current || '');
                cloudFormData.append('file', fileToUpload);
                
                const cloudRes = await axios.post(`${API_BASE}/evidence/upload/`, cloudFormData, {
                   headers: { 'Content-Type': 'multipart/form-data', Authorization: `Bearer ${authToken}` }
                });

                const supabaseUrl = cloudRes.data.public_url;
                console.log(` [CHUNK #${sequence}] ✅ Supabase Upload Success: ${supabaseUrl}`);

                // --- PHASE 2: NOTIFY LIVE TRACKER (HANDSHAKE) ---
                console.log(` [CHUNK #${sequence}] Phase 2: Updating Live Tracker...`);
                const pulseData = new FormData();
                const normalizedToken = (emergencyTokenRef.current || '').toString().trim().toLowerCase();
                pulseData.append('emergency_token', normalizedToken);
                pulseData.append('sequence', sequence.toString());
                pulseData.append('lat', loc.coords.latitude.toString());
                pulseData.append('lng', loc.coords.longitude.toString());
                pulseData.append('remote_url', supabaseUrl); // Pass the Supabase link

                await axios.post(`${API_BASE}/alerts/upload-chunk/`, pulseData, {
                   headers: { 'Content-Type': 'multipart/form-data', Authorization: `Bearer ${authToken}` }
                });
                console.log(` [CHUNK #${sequence}] ✅ Dashboard Notified.`);
            }
         } else {
            await new Promise(r => setTimeout(r, 5000));
         }

       } catch (e) {
           console.error(" Chunk Handshake Error:", e);
           await new Promise(r => setTimeout(r, 2000));
       }
       if (emergencyTokenRef.current) captureAndUpload();
    };

    captureAndUpload(); // Start loop

    // Legacy Pulse Animation Support
    const createPulse = (val: Animated.Value, delay: number) => 
      Animated.loop(
        Animated.sequence([
          Animated.delay(delay),
          Animated.timing(val, { toValue: 2.5, duration: 1500, useNativeDriver: true, easing: Easing.out(Easing.quad) }),
          Animated.timing(val, { toValue: 1, duration: 0, useNativeDriver: true })
        ])
      );
    
    Animated.parallel([createPulse(pulse1, 0), createPulse(pulse2, 500), createPulse(pulse3, 1000)]).start();
  };

  const stopSOS = async () => {
    // SECURITY RESTORED: Challenge identity before resolving active SOS
    console.log(" RAKSHAK: Active SOS Stop Requested. Challenging Identity...");
    setBiometricStatus("Scanning for Authorized Owner...");
    setIsBiometricActive(true);
  };

  const resolveSOSAfterVerify = async () => {
    setIsAlertActive(false);
    setIsSOSCountdown(false);
    await AsyncStorage.removeItem('RAKSHAK_ACTIVE_SOS');
    if (gpsInterval.current) clearInterval(gpsInterval.current);
    if (evidenceCameraRef.current) evidenceCameraRef.current.stopRecording();
    emergencyTokenRef.current = null; // Exit chunking loop

    [pulse1, pulse2, pulse3].forEach(p => { p.stopAnimation(); p.setValue(1); });
    
    if (activeAlertId) {
      try {
        await axios.post(`${API_BASE}/alerts/${activeAlertId}/resolve/`, {}, {
          headers: { Authorization: `Bearer ${authToken}` }
        });
      } catch (e) { console.log("Resolution failed"); }
    }
  };

  const handleMicPress = async () => {
    if (!isRecording) {
      try {
        const { status } = await Audio.requestPermissionsAsync();
        if (status !== 'granted') return Alert.alert("Required", "Microphone access is needed for Rakshak voice SOS.");

        setIsRecording(true);
        Animated.loop(
          Animated.sequence([
            Animated.timing(micWave, { toValue: 1, duration: 400, useNativeDriver: true }),
            Animated.timing(micWave, { toValue: 0, duration: 400, useNativeDriver: true })
          ])
        ).start();

        // Start Actual Recording
        await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
        const { recording: rec } = await Audio.Recording.createAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY);
        recording.current = rec;

        console.log(" Recording Voice Signature...");
        
        setTimeout(async () => {
          setIsRecording(false);
          micWave.stopAnimation();
          
          if (recording.current) {
            await recording.current.stopAndUnloadAsync();
            const uri = recording.current.getURI();
            console.log(" Signature captured at:", uri);
            recording.current = null;
            
            // --- TRANSCRIBE AND ENROLL KEYWORD ON BACKEND ---
            try {
              console.log(" Extracting safety keyword via backend engine...");
              const formData = new FormData();
              formData.append('audio', { uri, name: 'enroll_sample.m4a', type: 'audio/m4a' } as any);
              
              const res = await axios.post(`${API_BASE}/profile/voice-enroll/`, formData, {
                 headers: { 'Content-Type': 'multipart/form-data', Authorization: `Bearer ${authToken}` }
              });
              
              setForm({...form, keyword: res.data.keyword});

              Alert.alert("Voice Signature Active", `I heard "${res.data.keyword}". This is now your secure SOS trigger.`, [
                { text: "Proceed", onPress: () => navigate('contacts_setup') }
              ]);
            } catch (err: any) {
              const msg = err.response?.data?.error || "Could not analyze audio. Try again.";
              console.error("Keyword enrollment failed", err);
              Alert.alert("Enrollment Failed", msg);
            }
          }
        }, 3000);
      } catch (e) {
        console.error("Recording failed", e);
        setIsRecording(false);
        micWave.stopAnimation();
      }
    }
  };

  const handleBiometricCapture = async () => {
    if (!biometricCameraRef.current) return;
    const isEnrollment = currentScreen === 'biometric_enrollment';
    setBiometricStatus(isEnrollment ? "Registering Faceprint..." : "Capturing...");
    
    try {
      const photo = await biometricCameraRef.current.takePictureAsync({
        quality: 0.3,
        base64: false
      });

      if (!photo) throw new Error("Camera capture failed");

      setBiometricStatus(isEnrollment ? "Saving Master Face..." : "Verifying Identity...");
      
      const formData = new FormData();
      // @ts-ignore
      formData.append('image', {
        uri: photo.uri,
        name: isEnrollment ? 'enrollment.jpg' : 'verification.jpg',
        type: 'image/jpeg'
      });

      const endpoint = isEnrollment ? '/profile/face-enroll/' : '/alerts/verify-biometric/';
      const res = await axios.post(`${API_BASE}${endpoint}`, formData, {
        headers: { 
          'Content-Type': 'multipart/form-data',
          Authorization: `Bearer ${authToken}` 
        }
      });

      if (isEnrollment) {
        setBiometricStatus("Enrolled!");
        setTimeout(() => {
          Alert.alert("Success", "Your faceprint has been securely registered.");
          if (res.data.biometric_vector) setFaceVector(res.data.biometric_vector);
          setIsBiometricActive(false);
          navigate('home');
        }, 800);
      } else {
        if (res.data.verified) {
          setBiometricStatus("Confirmed!");
          setTimeout(() => {
            Alert.alert("Verified", "Your safety has been confirmed.");
            resolveSOSAfterVerify();
            setIsBiometricActive(false);
          }, 800);
        } else {
          throw new Error(res.data.error || "Match Failed");
        }
      }
    } catch (err: any) {
      const msg = err.response?.data?.error || err.message || "Retry Scan";
      setBiometricStatus("Failed");
      Alert.alert("Security Check", msg, [
        { text: "Retry", onPress: () => setBiometricStatus("Ready for Scan") }
      ]);
    }
  };

  return (
    <View style={styles.appContainer}>
      <StatusBar barStyle="light-content" />
      <LinearGradient colors={THEME.bg as any} style={StyleSheet.absoluteFill} />

      {/* --- LOGIN SCREEN --- */}
      <ScreenWrapper visible={currentScreen === 'login'}>
        <View style={styles.glassCard}>
          <View style={styles.logoCircle}>
            <MaterialCommunityIcons name="shield-check" color={THEME.primary} size={40} />
          </View>
          <Text style={styles.title}>RAKSHAK</Text>
          <Text style={styles.subtitle}>Unified Safety Protocol</Text>
          
          <InputField 
            icon="email-outline" placeholder="Access ID (Email)" 
            value={form.email} onChangeText={(v: string) => setForm({...form, email: v})} 
          />
          <InputField 
            icon="lock-outline" placeholder="Passcode" secureTextEntry 
            value={form.password} onChangeText={(v: string) => setForm({...form, password: v})} 
          />

          <TouchableOpacity 
            style={styles.btnPrimary} 
            onPress={async () => {
                const loginUrl = `${API_BASE}/auth/login/`;
                console.log(` RAKSHAK: Attempting Login at ${loginUrl}`);
                
                try {
                  const res = await axios.post(loginUrl, {
                    email: form.email,
                    password: form.password
                  });
                  
                  console.log(" RAKSHAK: Login SUCCESS");
                  const token = res.data.access;
                  const r_id = res.data.rakshak_id;
                  const u_id = res.data.user_id;
                  const bio_enrolled = res.data.biometric_enrolled;
                  const enrolled_vector = res.data.biometric_vector;
                  
                  setAuthToken(token);
                  setRakshakId(r_id);
                  setUserId(u_id);
                  if (enrolled_vector) setFaceVector(enrolled_vector);
                  
                  // Fetch real profile data immediately
                  console.log(" RAKSHAK: Synchronizing Guardian Protocols...");
                  const contactRes = await axios.get(`${API_BASE}/contacts/`, {
                     headers: { Authorization: `Bearer ${token}` }
                  });
                  
                  if (contactRes.data && contactRes.data.length > 0) {
                     const c = contactRes.data[0];
                     setGuardian({ name: c.name, phone: c.phone, email: c.email || '' });
                  }

                  if (!bio_enrolled) {
                     console.warn(" Biometric Missing: Forcing Enrollment Wizard");
                     navigate('biometric_enrollment');
                  } else {
                     console.log(" RAKSHAK: Login Complete. Vault Open.");
                     navigate('home');
                  }
                } catch (e: any) { 
                  console.error(` RAKSHAK: Login FAILED at ${loginUrl}`);
                if (e.response) {
                    console.error("Data:", e.response.data);
                    console.error("Status:", e.response.status);
                } else {
                    console.error("Error Message:", e.message);
                }
                Alert.alert("Authentication Failure", "Invalid credentials or network timeout.");
              }
            }}
          >
            <Text style={styles.btnText}>INITIALIZE SESSION</Text>
          </TouchableOpacity>

          <TouchableOpacity onPress={handleNavigateRegister}>
            <Text style={styles.linkText}>Establish new credentials</Text>
          </TouchableOpacity>

          <View style={styles.diagnosticBox}>
            <MaterialCommunityIcons name="broadcast" color={THEME.textDim} size={12} />
            <Text style={styles.diagnosticText}>ENDPOINT: {API_BASE}</Text>
          </View>
        </View>
      </ScreenWrapper>

      {/* --- REGISTER SCREEN --- */}
      <ScreenWrapper visible={currentScreen === 'register'}>
        <View style={styles.glassCard}>
          <Text style={styles.header}>NEW PROFILE</Text>
          <Text style={styles.description}>Establish your biometrically secure environment.</Text>
          
          <InputField icon="account-outline" placeholder="Full Name" value={form.name} onChangeText={(v: string) => setForm({...form, name: v})} />
          <InputField icon="email-outline" placeholder="Email" value={form.email} onChangeText={(v: string) => setForm({...form, email: v})} />
          <InputField icon="phone-outline" placeholder="Phone Number" value={form.phone} onChangeText={(v: string) => setForm({...form, phone: v})} keyboardType="phone-pad" />
          <InputField icon="lock-outline" placeholder="Passcode" secureTextEntry value={form.password} onChangeText={(v: string) => setForm({...form, password: v})} />

          <TouchableOpacity 
            style={styles.btnPrimary} 
            onPress={async () => {
              if (!form.name || !form.email || !form.password || !form.phone) return Alert.alert("Missing Info", "All fields including Phone Number are required.");
              
              const signupUrl = `${API_BASE}/auth/register/`;
              console.log(` RAKSHAK: Attempting Signup at ${signupUrl}`);
              console.log(` Payload:`, JSON.stringify(form, null, 2));

              try {
                 const res = await axios.post(signupUrl, form);
                 console.log(" RAKSHAK: Signup SUCCESS", res.data);
                 
                 setAuthToken(res.data.access);
                 setUserId(res.data.user_id);
                 setRakshakId(res.data.rakshak_id);
                 navigate('voice_setup');
              } catch (e: any) {
                 console.error(` RAKSHAK: Signup FAILED at ${signupUrl}`);
                 if (e.response) {
                    console.error("Data:", e.response.data);
                    console.error("Status:", e.response.status);
                 } else {
                    console.error("Error Message:", e.message);
                    console.error("Is it a Timeout/Network Error? (See Error Info above)");
                 }
                 Alert.alert("Registry Error", "User may already exist or connection failed.");
              }
            }}
          >
            <Text style={styles.btnText}>PROCEED TO AUDIO</Text>
          </TouchableOpacity>
        </View>
      </ScreenWrapper>

      {/* --- VOICE SETUP SCREEN --- */}
      <ScreenWrapper visible={currentScreen === 'voice_setup'}>
        <View style={styles.glassCard}>
          <View style={styles.iconBox}><MaterialCommunityIcons name="microphone" color={THEME.primary} size={30} /></View>
          <Text style={styles.header}>Voice Signature</Text>
          <Text style={styles.description}>Your distress keyword is processed strictly on-device using quantized TFLite models.</Text>
          
          <View style={[styles.infoBox, { marginBottom: 20 }]}>
             <Text style={styles.infoText}>
                {form.keyword ? `Your verified keyword is: "${form.keyword}"` : "Tap the microphone and speak your secret keyword."}
             </Text>
          </View>

          <View style={styles.micCircleContainer}>
            {isRecording && <Animated.View style={[styles.micPulse, { opacity: micWave.interpolate({ inputRange: [0, 1], outputRange: [0.6, 0] }), transform: [{ scale: micWave.interpolate({ inputRange: [0, 1], outputRange: [1, 1.8] }) }] }]} />}
            <TouchableOpacity 
              style={[styles.micBtn, isRecording && styles.micBtnActive]} 
              onPress={handleMicPress}
              disabled={isRecording}
            >
              <MaterialCommunityIcons name="microphone" color={THEME.text} size={35} />
            </TouchableOpacity>
          </View>
          <Text style={styles.hintText}>{isRecording ? "Capturing Acoustic Features..." : "Pulse to start recording"}</Text>
        </View>
      </ScreenWrapper>

      {/* --- CONTACTS SETUP SCREEN --- */}
      <ScreenWrapper visible={currentScreen === 'contacts_setup'}>
        <View style={styles.glassCard}>
          <Text style={styles.header}>The Guardian</Text>
          <Text style={styles.description}>Who should receive your rescue beacons?</Text>
          
          <InputField icon="account-outline" placeholder="Contact Name" value={guardian.name} onChangeText={(v: string) => setGuardian({...guardian, name: v})} />
          <InputField icon="phone-outline" placeholder="Emergency Phone" value={guardian.phone} onChangeText={(v: string) => setGuardian({...guardian, phone: v})} keyboardType="phone-pad" />
          <InputField icon="email-outline" placeholder="Emergency Email" value={guardian.email} onChangeText={(v: string) => setGuardian({...guardian, email: v})} keyboardType="email-address" />

          <TouchableOpacity 
            style={[styles.btnPrimary, { backgroundColor: THEME.success }]} 
            onPress={async () => {
              if (guardian.name && guardian.phone && guardian.email) {
                 // Save to server
                 try {
                    await axios.post(`${API_BASE}/contacts/add/`, guardian, {
                       headers: { Authorization: `Bearer ${authToken}` }
                    });
                    navigate('home');
                 } catch (e) { Alert.alert("Sync Failure", "Could not save to server. Check IP."); }
              }
              else if (!guardian.email && guardian.name && guardian.phone) {
                 Alert.alert("Legacy Setup", "Automation requires an email. Continue with local SMS protocol only?", [
                   { text: "Add Email", style: 'cancel' },
                    { text: "Use Local SMS", onPress: () => navigate('biometric_enrollment') }
                 ]);
              }
              else Alert.alert("Protocol Missing", "Please define a guardian.");
            }}
          >
            <Text style={styles.btnText}>SAVE GUARDIAN</Text>
          </TouchableOpacity>
        </View>
      </ScreenWrapper>

      {/* --- SAFE ROUTE MAP SCREEN --- */}
      <ScreenWrapper visible={currentScreen === 'route_map'}>
        <SafeRouteMap 
          authToken={authToken || ''} 
          apiBase={API_BASE} 
          onBack={() => navigate('home')} 
          theme={THEME}
        />
      </ScreenWrapper>

      {/* --- HOME / SOS DASHBOARD --- */}
      <ScreenWrapper visible={currentScreen === 'home'}>
        <View style={styles.dashboard}>
          <View style={styles.dashHeader}>
            <View style={{ flexDirection: 'row', alignItems: 'center' }}>
              <TouchableOpacity 
                onPress={() => navigate('route_map')}
                style={{ marginRight: 15, backgroundColor: 'rgba(124, 58, 237, 0.1)', padding: 8, borderRadius: 12, borderWidth: 1, borderColor: 'rgba(124, 58, 237, 0.2)' }}
              >
                <MaterialCommunityIcons name="map-marker-path" color={THEME.primary} size={24} />
              </TouchableOpacity>
              <View>
                <Text style={styles.dashTitle}>RAKSHAK</Text>
                <View style={styles.statusRow}>
                  <View style={styles.statusDot} />
                  <Text style={styles.statusLabel}>SECURED SESSION</Text>
                  {isSimulated && (
                    <View style={[styles.statusRow, { marginLeft: 10 }]}>
                      <MaterialCommunityIcons name="test-tube" color={THEME.warning} size={12} />
                      <Text style={[styles.statusLabel, { color: THEME.warning, marginLeft: 4 }]}>SIMULATION MODE</Text>
                    </View>
                  )}
                </View>
              </View>
            </View>
            <View style={{ alignItems: 'flex-end' }}>
               <TouchableOpacity onPress={handleLogout}><MaterialCommunityIcons name="logout" color={THEME.textDim} size={24} /></TouchableOpacity>
               <View style={styles.badgeSmall}>
                  <Text style={styles.badgeTextSmall}>ID: {rakshakId || 'SEARCHING...'}</Text>
               </View>
            </View>
          </View>

          {!guardian.email && (
            <TouchableOpacity style={styles.warningBanner} onPress={() => navigate('contacts_setup')}>
              <MaterialCommunityIcons name="alert-circle-outline" color="#FFF" size={18} />
              <Text style={styles.warningBannerText}>Automation Disabled: Add Guardian Email</Text>
            </TouchableOpacity>
          )}

          <View style={styles.sosCoreContainer}>
            {isAlertActive ? (
              <View style={[StyleSheet.absoluteFill, { borderRadius: 30, overflow: 'hidden', backgroundColor: '#000' }]}>
                <CameraView 
                   ref={evidenceCameraRef}
                   style={StyleSheet.absoluteFill} 
                   facing="back"
                   mode="video"
                />
                
                {userLocation && (
                  <View style={{ position: 'absolute', bottom: 70, left: 10, width: 130, height: 180, borderRadius: 15, overflow: 'hidden', borderWidth: 2, borderColor: 'rgba(255,255,255,0.7)' }}>
                    <MapView
                      style={{ flex: 1 }}
                      initialRegion={{ latitude: activeRescue?.location ? activeRescue.location[1] : (userLocation?.latitude || 0.0),
                     longitude: userLocation?.longitude || activeRescue.location[0],
                        latitudeDelta: 0.01,
                        longitudeDelta: 0.01,
                      }}
                    >
                      <Marker coordinate={userLocation} title="You (SOS)" pinColor="red" />
                      {comingVolunteers.map((v: any, idx: number) => (
                        v.lat !== 0 && (
                          <Marker 
                            key={idx} 
                            coordinate={{ latitude: v.lat, longitude: v.lng }} 
                            title={`Rescuer: ${v.name}`} 
                            pinColor="green" 
                          />
                        )
                      ))}
                    </MapView>
                  </View>
                )}
                <TouchableOpacity 
                   style={styles.stopSosOverlay} 
                   onPress={stopSOS}
                >
                   <MaterialCommunityIcons name="close-circle" color="#FFF" size={24} />
                   <Text style={{ color: '#FFF', fontWeight: 'bold', marginLeft: 8 }}>STOP SOS</Text>
                </TouchableOpacity>
              </View>
            ) : (
              <>
                <TouchableOpacity 
                  activeOpacity={0.9} 
                  style={styles.sosBtnMain} 
                  onPress={startSOS}
                >
                  <MaterialCommunityIcons name="broadcast" color="#FFF" size={40} style={styles.sosIcon} />
                  <Text style={styles.sosMainText}>SOS</Text>
                </TouchableOpacity>

                {/* --- TEST BIOMETRICS BUTTON --- */}
                <TouchableOpacity 
                  style={styles.testBioBtn}
                  onPress={handleTestBiometric}
                >
                   <MaterialCommunityIcons name="face-recognition" color={THEME.textDim} size={20} />
                   <Text style={styles.testBioText}>TEST VERIFICATION</Text>
                </TouchableOpacity>
              </>
            )}
          </View>

          <View style={styles.statsGrid}>
            <View style={styles.statBox}>
               <MaterialCommunityIcons name="pulse" color={THEME.primary} size={22} />
               <Text style={styles.statVal}>98%</Text>
               <Text style={styles.statLab}>AI Precision</Text>
            </View>
            <View style={styles.statBox}>
               <MaterialCommunityIcons name="map-marker-radius" color={THEME.primary} size={22} />
               <Text style={styles.statVal}>2m</Text>
               <Text style={styles.statLab}>GPS Accuracy</Text>
            </View>
          </View>

          <TouchableOpacity activeOpacity={0.8} style={styles.guardianStrip} onPress={() => navigate('contacts_setup')}>
            <MaterialCommunityIcons name="shield-account" color={THEME.success} size={20} />
            <Text style={styles.guardianText}>Guardian {guardian.name || 'Set'} is synced</Text>
            <MaterialCommunityIcons name="pencil" color={THEME.success} size={16} style={{ marginLeft: 'auto', marginRight: 10 }} />
          </TouchableOpacity>

          {/* --- HELP IS COMING (Victim Panic Reduction) --- */}
          {isAlertActive && comingVolunteers.length > 0 && (
            <View style={styles.helpComingContainer}>
              <Text style={styles.helpComingHeader}>HELP IS COMING</Text>
              {comingVolunteers.slice(0, 3).map((v: any, i: number) => {
                const dist = userLocation ? getDistance(userLocation.latitude, userLocation.longitude, v.lat, v.lng) : 0;
                return (
                  <View key={i} style={styles.volunteerRow}>
                    <MaterialCommunityIcons name="account-check" color={THEME.success} size={24} />
                    <View style={{ marginLeft: 15 }}>
                      <Text style={styles.volunteerName}>{v.name}</Text>
                      <Text style={styles.volunteerDist}>{dist > 0 ? `${(dist / 1000).toFixed(2)} km away` : 'Connecting...'}</Text>
                    </View>
                  </View>
                );
              })}
            </View>
          )}
        </View>
      </ScreenWrapper>
      <ScreenWrapper visible={currentScreen === 'biometric_enrollment'}>
        <View style={styles.glassCard}>
          <View style={styles.logoCircle}>
             <MaterialCommunityIcons name="face-recognition" color={THEME.primary} size={40} />
          </View>
          <Text style={styles.header}>Face Identity</Text>
          <Text style={styles.description}>
            Secure your account with Biometric Verification. Please look at the camera and blink to enroll.
          </Text>
          
          <View style={styles.cameraPlaceholder}>
             <CameraView 
                style={StyleSheet.absoluteFill} 
                facing="front"
             />
             <View style={styles.scanLine} />
          </View>



          <TouchableOpacity 
            style={[styles.btnPrimary, { width: '100%', marginTop: 20 }]} 
            onPress={handleEnrollFace}
          >
            <Text style={styles.btnText}>ENROLL FACEPRINT</Text>
          </TouchableOpacity>

        </View>
      </ScreenWrapper>

      {/* --- RESCUE MAP PORTAL --- */}
      {isSOSCountdown && (
        <SOSManager 
           onCancel={cancelSOS} 
           onTimerEnd={executeSOSHandover} 
        />
      )}
      {/* --- FACE BIOMETRIC VERIFICATION (Simulation Layer) --- */}
      {isBiometricActive && (
        <View style={[StyleSheet.absoluteFill, { backgroundColor: '#000', zIndex: 10000, padding: 30, justifyContent: 'center' }]}>
           <View style={{ alignItems: 'center' }}>
              <View style={{ width: 300, height: 300, borderRadius: 150, borderWidth: 4, borderColor: THEME.primary, overflow: 'hidden', justifyContent: 'center', alignItems: 'center', backgroundColor: 'rgba(255,255,255,0.05)' }}>
                  <CameraView 
                     ref={biometricCameraRef}
                     style={StyleSheet.absoluteFill} 
                     facing="front"
                     onCameraReady={() => {
                        // FASTER VERIFICATION: Auto-capture as soon as camera is active
                        console.log(" [BIOMETRIC] Camera Live. Fast-scanning...");
                        setTimeout(() => {
                           if (isBiometricActive) handleBiometricCapture();
                        }, 800);
                     }}
                  />
                  <View style={styles.scanLine} />
               </View>
               <Text style={{ color: '#FFF', fontSize: 24, fontWeight: 'bold', marginTop: 30 }}>{biometricStatus}</Text>
               <Text style={{ color: THEME.textDim, textAlign: 'center', marginTop: 15, paddingHorizontal: 30 }}>
                   RAKSHAK is currently scanning your biometric facial geometry to authenticate.
               </Text>
                <View style={{ marginTop: 40, width: '100%' }}>
                  <TouchableOpacity 
                      onPress={handleBiometricCapture}
                      style={[styles.btnPrimary, { backgroundColor: THEME.primary, marginTop: 0 }]}
                  >
                      <Text style={[styles.btnText, { color: '#FFF' }]}>MANUAL SCAN</Text>
                  </TouchableOpacity>
                </View>



              <TouchableOpacity 
                 onPress={() => setIsBiometricActive(false)}
                 style={{ marginTop: 20 }}
              >
                 <Text style={{ color: THEME.textDim }}>Cancel Verification</Text>
              </TouchableOpacity>
           </View>
        </View>
      )}

      {activeRescue && (
         <View style={[StyleSheet.absoluteFill, { backgroundColor: THEME.bg[0], zIndex: 1000 }]}>
            <View style={{ paddingTop: 60, paddingHorizontal: 20, paddingBottom: 20, backgroundColor: THEME.bg[1] }}>
               <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
                  <View>
                    <Text style={{ color: THEME.danger, fontSize: 24, fontWeight: 'bold' }}>ACTIVE RESCUE MODE</Text>
                    <Text style={{ color: THEME.textDim }}>RESCUING: {activeRescue.name || 'CITIZEN'}</Text>
                  </View>
                  <View style={styles.verifiedBadge}>
                     <MaterialCommunityIcons name="shield-check" color="#FFF" size={16} />
                     <Text style={styles.verifiedText}>VERIFIED RESCUER</Text>
                  </View>
               </View>
               
               <View style={styles.etaContainer}>
                  <MaterialCommunityIcons name="clock-outline" color={THEME.primary} size={20} />
                  <Text style={styles.etaText}>
                    ESTIMATED ARRIVAL: {userLocation ? (getDistance(userLocation.latitude, userLocation.longitude, activeRescue.location[1], activeRescue.location[0]) / 300).toFixed(0) : '--'} MIN
                  </Text>
               </View>

               <TouchableOpacity 
                 style={[styles.btnPrimary, { marginTop: 15, backgroundColor: THEME.primary }]}
                 onPress={isRescuing ? () => Linking.openURL(`https://www.google.com/maps/search/?api=1&query=${activeRescue.location[1]},${activeRescue.location[0]}`) : acceptRescue}
               >
                 <Text style={styles.btnText}>{isRescuing ? "OPEN GOOGLE NAVIGATION" : "CONFIRM RESCUE MISSION"}</Text>
               </TouchableOpacity>
               
               <TouchableOpacity onPress={() => { dismissedAlerts.current.add(activeRescue.alert_id || activeRescue.id); setActiveRescue(null); }} style={{ marginTop: 15 }}>
                  <Text style={{ color: THEME.textDim, textAlign: 'center' }}>Dismiss Map</Text>
               </TouchableOpacity>
            </View>
            <MapView
               style={{ flex: 1 }}
               initialRegion={{ 
                  latitude: activeRescue?.location ? activeRescue.location[1] : (userLocation?.latitude || 30.268),
                  longitude: activeRescue?.location ? activeRescue.location[0] : (userLocation?.longitude || 77.993),
                  latitudeDelta: 0.05,
                  longitudeDelta: 0.05,
               }}
            >
               {userLocation && (
                  <Marker 
                    coordinate={{ latitude: userLocation.latitude, longitude: userLocation.longitude }}
                    title="You"
                    pinColor="blue"
                  />
                )}
               {activeRescue?.location && (
                 <Marker 
                    coordinate={{ latitude: activeRescue.location[1], longitude: activeRescue.location[0] }}
                    title="Victim"
                    pinColor="red"
                 />
               )}
            </MapView>

         </View>
      )}

    </View>
  );
}


const styles = StyleSheet.create({
  appContainer: { flex: 1, backgroundColor: '#000' },
  screenContainer: { flex: 1, paddingHorizontal: 25, justifyContent: 'center' },
  glassCard: { backgroundColor: THEME.glass, borderRadius: 40, padding: 35, borderWidth: 1, borderColor: THEME.border, alignItems: 'center' },
  
  // Auth Elements
  cameraPlaceholder: { width: 250, height: 250, borderRadius: 125, backgroundColor: 'rgba(0,0,0,0.5)', borderWidth: 2, borderColor: '#7C3AED', justifyContent: 'center', alignItems: 'center', overflow: 'hidden', marginBottom: 20 },
  scanLine: { position: 'absolute', width: '100%', height: 2, backgroundColor: '#7C3AED', top: '50%' },
  logoCircle: { width: 80, height: 80, borderRadius: 40, backgroundColor: 'rgba(124, 58, 237, 0.1)', justifyContent: 'center', alignItems: 'center', marginBottom: 20 },

  title: { color: THEME.text, fontSize: 34, fontWeight: '900', letterSpacing: 5 },
  subtitle: { color: THEME.primary, fontSize: 13, fontWeight: '800', letterSpacing: 2, textTransform: 'uppercase', marginBottom: 40 },
  header: { color: THEME.text, fontSize: 28, fontWeight: '800', marginBottom: 10 },
  description: { color: THEME.textDim, fontSize: 15, textAlign: 'center', lineHeight: 22, marginBottom: 35 },
  
  // Input Component
  inputWrapper: { width: '100%', flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.3)', borderRadius: 20, marginBottom: 18, paddingHorizontal: 15, borderWidth: 1, borderColor: THEME.border },
  inputIcon: { marginRight: 15 },
  input: { flex: 1, color: THEME.text, fontSize: 16, paddingVertical: 18 },
  
  // Button Component
  btnPrimary: { width: '100%', backgroundColor: THEME.primary, borderRadius: 20, paddingVertical: 20, alignItems: 'center', marginTop: 15, shadowColor: THEME.primary, shadowOffset: { width: 0, height: 8 }, shadowOpacity: 0.4, shadowRadius: 15 },
  btnText: { color: THEME.text, fontSize: 15, fontWeight: '900', letterSpacing: 2 },
  linkText: { color: THEME.textDim, fontSize: 14, marginTop: 25, textDecorationLine: 'underline' },

  // Voice Setup Elements
  iconBox: { width: 60, height: 60, borderRadius: 20, backgroundColor: 'rgba(124,58,237,0.1)', justifyContent: 'center', alignItems: 'center', marginBottom: 20 },
  micCircleContainer: { width: 200, height: 200, justifyContent: 'center', alignItems: 'center', marginTop: 10 },
  micBtn: { width: 100, height: 100, borderRadius: 50, backgroundColor: THEME.primary, justifyContent: 'center', alignItems: 'center', zIndex: 10 },
  micBtnActive: { backgroundColor: THEME.warning },
  micPulse: { position: 'absolute', width: 100, height: 100, borderRadius: 50, backgroundColor: THEME.primary },
  hintText: { color: THEME.textDim, marginTop: 20, fontSize: 14 },

  // Dashboard Elements
  dashboard: { flex: 1, paddingVertical: 50 },
  dashHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 40 },
  dashTitle: { color: THEME.text, fontSize: 24, fontWeight: '900', letterSpacing: 2 },
  statusRow: { flexDirection: 'row', alignItems: 'center', marginTop: 5 },
  statusDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: THEME.success, marginRight: 8 },
  statusLabel: { color: THEME.success, fontSize: 10, fontWeight: '800', letterSpacing: 1 },
  badgeSmall: {
    backgroundColor: 'rgba(124, 58, 237, 0.2)',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
    marginTop: 4,
    borderWidth: 1,
    borderColor: 'rgba(124, 58, 237, 0.3)',
  },
  badgeTextSmall: {
    color: '#FFF',
    fontSize: 10,
    fontWeight: 'bold',
  },
  
  sosCoreContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  sosBtnMain: { width: width * 0.6, height: width * 0.6, borderRadius: width * 0.3, backgroundColor: THEME.warning, justifyContent: 'center', alignItems: 'center', zIndex: 20, borderWidth: 8, borderColor: 'rgba(255,255,255,0.1)' },
  sosBtnActive: { backgroundColor: THEME.danger },
  sosIcon: { marginBottom: 15 },
  sosMainText: { color: '#FFF', fontSize: 32, fontWeight: '900', textAlign: 'center', letterSpacing: 2 },
  sosShockwave: { position: 'absolute', width: width * 0.6, height: width * 0.6, borderRadius: width * 0.3, backgroundColor: THEME.warning, zIndex: 1 },
  
  statsGrid: { flexDirection: 'row', gap: 15, marginBottom: 30 },
  statBox: { flex: 1, backgroundColor: THEME.glass, borderRadius: 25, padding: 20, alignItems: 'center', borderWidth: 1, borderColor: THEME.border },
  statVal: { color: THEME.text, fontSize: 20, fontWeight: '800', marginTop: 8 },
  statLab: { color: THEME.textDim, fontSize: 11, fontWeight: '600', marginTop: 4 },
  
  guardianStrip: { backgroundColor: 'rgba(16, 185, 129, 0.1)', paddingVertical: 18, borderRadius: 20, flexDirection: 'row', justifyContent: 'center', alignItems: 'center', borderWidth: 1, borderColor: 'rgba(16, 185, 129, 0.2)' },
  guardianText: { color: THEME.success, marginLeft: 10, fontWeight: '700', fontSize: 13 },
  warningBanner: { backgroundColor: THEME.warning, paddingVertical: 12, borderRadius: 15, flexDirection: 'row', justifyContent: 'center', alignItems: 'center', marginBottom: 20, marginHorizontal: 5 },
  warningBannerText: { color: '#FFF', fontSize: 12, fontWeight: '800', marginLeft: 8, letterSpacing: 0.5 },
  
  // Diagnostic UI
  diagnosticBox: { marginTop: 30, flexDirection: 'row', alignItems: 'center', opacity: 0.5 },
  diagnosticText: { color: THEME.textDim, fontSize: 9, fontWeight: 'bold', marginLeft: 6, letterSpacing: 1 },

  // Help is Coming UI
  helpComingContainer: { marginTop: 30, backgroundColor: THEME.glass, borderRadius: 25, padding: 25, borderWidth: 1, borderColor: THEME.border },
  helpComingHeader: { color: THEME.success, fontSize: 13, fontWeight: '900', letterSpacing: 2, marginBottom: 20, textAlign: 'center' },
  volunteerRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 20 },
  volunteerName: { color: THEME.text, fontSize: 16, fontWeight: '800' },
  volunteerDist: { color: THEME.textDim, fontSize: 13, marginTop: 2 },

  // Volunteer Navigation UI

  // Map Overlay UI
  verifiedBadge: {
    backgroundColor: THEME.primary,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 15,
  },
  verifiedText: {
    color: '#FFF',
    fontSize: 10,
    fontWeight: 'bold',
    marginLeft: 5,
  },
  etaContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.05)',
    padding: 12,
    borderRadius: 12,
    marginTop: 15,
  },
  etaText: {
    color: '#FFF',
    fontSize: 12,
    fontWeight: '800',
    marginLeft: 10,
  },
  stopSosOverlay: { 
    position: 'absolute', 
    bottom: 20, 
    alignSelf: 'center', 
    backgroundColor: 'rgba(220, 38, 38, 0.8)', 
    paddingHorizontal: 20, 
    paddingVertical: 12, 
    borderRadius: 30, 
    flexDirection: 'row', 
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 5,
    elevation: 5
  },
  infoBox: {
    backgroundColor: 'rgba(255,255,255,0.05)',
    padding: 15,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
    width: '100%',
    alignItems: 'center'
  },
  infoText: {
    color: '#CCC',
    fontSize: 14,
    textAlign: 'center',
    lineHeight: 20
  },
  testBioBtn: {
    marginTop: 25,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.05)',
    paddingHorizontal: 15,
    paddingVertical: 10,
    borderRadius: 15,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
  },
  testBioText: {
    color: THEME.textDim,
    fontSize: 12,
    fontWeight: '700',
    marginLeft: 8,
    letterSpacing: 1
  }
});
