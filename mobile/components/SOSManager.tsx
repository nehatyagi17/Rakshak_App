import React, { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Animated, Easing } from 'react-native';
import { useKeepAwake } from 'expo-keep-awake';
import { ShieldAlert, ShieldCheck } from 'lucide-react-native';
import { LinearGradient } from 'expo-linear-gradient';

interface SOSManagerProps {
  onCancel: () => void;
  onTimerEnd: () => void;
}

export const SOSManager: React.FC<SOSManagerProps> = ({ onCancel, onTimerEnd }) => {
  useKeepAwake(); // Prevent screen sleep during SOS
  const [timeLeft, setTimeLeft] = useState(15);
  const scaleAnim = new Animated.Value(1);

  useEffect(() => {
    // Pulse animation for the timer
    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(scaleAnim, { toValue: 1.15, duration: 500, useNativeDriver: true, easing: Easing.inOut(Easing.ease) }),
        Animated.timing(scaleAnim, { toValue: 1, duration: 500, useNativeDriver: true, easing: Easing.inOut(Easing.ease) }),
      ])
    );
    pulse.start();

    const timer = setInterval(() => {
      setTimeLeft(prev => Math.max(0, prev - 1));
    }, 1000);

    return () => {
      clearInterval(timer);
      pulse.stop();
    };
  }, []);

  useEffect(() => {
    if (timeLeft <= 0) {
      onTimerEnd();
    }
  }, [timeLeft, onTimerEnd]);

  return (
    <View style={StyleSheet.absoluteFill}>
      <LinearGradient colors={['#FF0000', '#8B0000', '#000000']} style={styles.container}>
        <View style={styles.inner}>
          
          <Animated.View style={[styles.iconContainer, { transform: [{ scale: scaleAnim }] }]}>
            <ShieldAlert size={120} color="#FFF" />
          </Animated.View>

          <Text style={styles.header}>SOS INITIALIZED</Text>
          <Text style={styles.subHeader}>HANDOVER IN PROGRESS</Text>

          <View style={styles.timerCircle}>
            <Animated.Text style={[styles.timerText, { transform: [{ scale: scaleAnim }] }]}>
              {timeLeft}
            </Animated.Text>
            <Text style={styles.timerLabel}>SECONDS</Text>
          </View>

          <View style={styles.infoBox}>
            <Text style={styles.infoText}>
               If this is an error, press the button below immediately.
            </Text>
            <Text style={styles.criticalText}>
               HANDOVER TO AUTHORITY IN {timeLeft}S
            </Text>
          </View>

          <TouchableOpacity style={styles.cancelBtn} onPress={onCancel} activeOpacity={0.8}>
             <ShieldCheck size={28} color="#000" />
             <Text style={styles.cancelText}>I AM SAFE / CANCEL</Text>
          </TouchableOpacity>
          
        </View>
      </LinearGradient>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    zIndex: 9999,
  },
  inner: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 30,
  },
  iconContainer: {
    marginBottom: 20,
    shadowColor: '#FFF',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.5,
    shadowRadius: 20,
  },
  header: {
    color: '#FFF',
    fontSize: 38,
    fontWeight: '900',
    textAlign: 'center',
    letterSpacing: 2,
  },
  subHeader: {
    color: '#FFB800',
    fontSize: 18,
    fontWeight: 'bold',
    marginTop: 5,
    letterSpacing: 1,
  },
  timerCircle: {
    width: 200,
    height: 200,
    borderRadius: 100,
    borderWidth: 8,
    borderColor: 'rgba(255,255,255,0.2)',
    alignItems: 'center',
    justifyContent: 'center',
    marginVertical: 40,
    backgroundColor: 'rgba(0,0,0,0.3)',
  },
  timerText: {
    color: '#FFF',
    fontSize: 100,
    fontWeight: '900',
  },
  timerLabel: {
    color: 'rgba(255,255,255,0.6)',
    fontSize: 14,
    fontWeight: 'bold',
    marginTop: -10,
  },
  infoBox: {
    backgroundColor: 'rgba(0,0,0,0.5)',
    padding: 20,
    borderRadius: 15,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
    width: '100%',
    marginBottom: 40,
  },
  infoText: {
    color: '#CCC',
    textAlign: 'center',
    fontSize: 16,
    lineHeight: 22,
  },
  criticalText: {
    color: '#FF4444',
    textAlign: 'center',
    fontSize: 14,
    fontWeight: 'bold',
    marginTop: 10,
  },
  cancelBtn: {
    backgroundColor: '#FFF',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 20,
    paddingHorizontal: 40,
    borderRadius: 40,
    width: '100%',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.3,
    shadowRadius: 15,
    elevation: 10,
  },
  cancelText: {
    color: '#000',
    fontSize: 18,
    fontWeight: '900',
    marginLeft: 15,
  }
});
