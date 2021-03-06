from abc import ABC, abstractmethod
from libs.bh1792glc.driver import BH1792GLCDriver
from ctypes import c_bool
from multiprocessing import Process, Value
from multiprocessing.sharedctypes import Synchronized
from serial import Serial
from smbus2 import SMBus
from time import sleep, time


class SensorBase(ABC):
    """
    センサーを表す抽象基底クラス

    Attributes
    ----------
    _is_active : multiprocessing.sharedctypes.Synchronized(ctypes.c_bool)
        センサが値を更新しているか(問題なく動いているか)
    _p : multiprocessing.Process
        センサーの値を取得してメンバを更新していく並列プロセス
    """

    @abstractmethod
    def __init__(self):
        """
        センサ情報を登録してから、セットアップとデータ更新プロセスを開始する
        """
        self._is_active = Value(c_bool, True)
        try:
            self._setup()
            sleep(1)
        except Exception as e:
            print(type(e), e, "[in setup]")
            self._close()
        else:
            self._p = Process(target=self._process, args=())
            self._p.start()

    @abstractmethod
    def _close(self):
        """
        センサー自体を閉じるメソッド。i2cのバスを閉じて、プロセスの実行も止める
        """
        pass

    @abstractmethod
    def _setup(self):
        """
        接続前のモード設定などをする
        """
        pass

    @abstractmethod
    def _update(self):
        """
        センサーの値を読みメンバを更新する
        """
        pass

    """
    以下はオーバーライドしない想定のメソッド
    """

    def _process(self):
        """
        センサーの値を取得してメンバを更新するプロセス
        """
        try:
            while self._is_active.value:
                self._update()
                sleep(1)
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(type(e), e)
        finally:
            self._close()

    @property
    def status_dict(self):
        """
        センサの値を表すメンバを辞書として返す。外部からは`センサーインスタンス.status_dict`のように、メンバとして呼び出せる

        Returns
        -------
        status_dict : dict[str, float or str]
            Publicメンバの値の辞書
        """

        def restore(data):
            """
            Synchronized型のデータをPythonで直接扱える形式に復元する

            Parameters
            ----------
            data : multiprocessing.sharedctypes.Synchronized(ctypes.c_bool) or other(default python type)
                復元したいデータ

            Returns
            -------
            data : float or str
                復元されたデータ、もしくはそのままPythonで扱える型のデータ
            """
            if isinstance(data, Synchronized):
                return data.value
            return data

        return {k: restore(v) for k, v in self.__dict__.items() if not k.startswith("_")}

    @property
    def is_active(self):
        """
        このセンサが動いているかを返す

        Returns
        -------
        self._is_active.value : bool
            _is_activeの値
        """
        return self._is_active.value


class I2CSensorBase(SensorBase):
    """
    I2Cセンサーを表すクラス。__init__と_closeをオーバーライドしているため、このクラスを継承したクラスでは_setupと_processのみ実装すればよい

    Attributes
    ----------
    _bus : smbus2.SMBus
        I2Cのバス
    _address : int
        センサーのI2C(スレーブ)アドレス
    _is_active : multiprocessing.sharedctypes.Synchronized(ctypes.c_bool)
        センサが値を更新しているか(問題なく動いているか)
    _p : multiprocessing.Process
        センサーの値を取得してメンバを更新していく並列プロセス
    """
    def __init__(self, address):
        """
        Parameters
        ----------
        address : int
            I2Cスレーブのアドレス
        """
        self._bus = SMBus(1)
        self._address = address
        super().__init__()

    def _close(self):
        if isinstance(self._bus, SMBus):
            self._bus.close()
        self._is_active.value = False


class SerialSensorBase(SensorBase):
    """
    シリアルセンサーを表すクラス。__init__と_closeをオーバーライドしているため、このクラスを継承したクラスでは_setupと_processのみ実装すればよい

    Attributes
    ----------
    _ser : serial.Serial
        シリアル通信の接続
    _signal : str
        シリアル通信で送るシグナル
    _lock : multiprocessing.Lock
        メモリ保護のためのロック機構
    _retry : int
        シリアル通信に失敗した(=リトライした)回数
    _is_active : multiprocessing.sharedctypes.Synchronized(ctypes.c_bool)
        センサが値を更新しているか(問題なく動いているか)
    _p : multiprocessing.Process
        センサーの値を取得してメンバを更新していく並列プロセス
    """
    def __init__(self, signal, lock):
        """
        Parameters
        ----------
        signal : str
            シリアル通信で送るシグナル
        lock : multiprocessing.Lock
            メモリ保護のためのロック機構
        """
        self._ser = Serial("/dev/ttyACM0", 9600)
        self._signal = signal
        self._lock = lock
        self._retry = 0
        super().__init__()

    def _close(self):
        if isinstance(self._ser, Serial):
            self._ser.close()
        self._is_active.value = False


# 以下具象サブクラス


class PressureSensor(I2CSensorBase):
    """
    圧力センサーを表すクラス

    Attributes
    ----------
    type : str
        センサーの種類(圧力センサー)
    model_number : str
        センサーの型番
    measured_time : multiprocessing.sharedctypes.Synchronized(ctypes.c_bool)
        現在保持しているデータを取得した時間
    pressure_hpa : multiprocessing.sharedctypes.Synchronized(ctypes.c_bool)
        圧力[hPa]
    temperature_celsius : multiprocessing.sharedctypes.Synchronized(ctypes.c_bool)
        摂氏温度[℃]
    altitude_meters : multiprocessing.sharedctypes.Synchronized(ctypes.c_bool)
        推定高度[m]
    _bus : smbus2.SMBus
        i2cのバス
    _address : int
        センサーのi2cアドレス
    _is_active : multiprocessing.sharedctypes.Synchronized(ctypes.c_bool)
        センサが値を更新しているか(問題なく動いているか)
    _p : multiprocessing.Process
        センサーの値を取得してメンバを更新していく並列プロセス
    """

    def __init__(self, address=0x5C):
        """
        センサ情報を登録してから、セットアップとデータ更新プロセスを開始する

        Parameters
        ----------
        _address : int, default 0x5C
            センサーのi2cアドレス
        """
        self.type = "pressure_sensor"
        self.model_number = "LPS251B"
        self.measured_time = Value("d", 0.0)
        self.pressure_hpa = Value("d", 0.0)
        self.temperature_celsius = Value("d", 0.0)
        self.altitude_meters = Value("d", 0.0)
        super().__init__(address)

    def _setup(self):
        self._bus.write_byte_data(self._address, 0x20, 0xC0)  # 25Hz

    def _update(self):
        press, temp = self.__read_datas()

        self.measured_time.value = time()
        self.pressure_hpa.value = self.__convert_pressure(press)
        self.temperature_celsius.value = self.__convert_temperature(temp)
        self.altitude_meters.value = self.__convert_altitude(self.pressure_hpa.value, self.temperature_celsius.value)

    def __read_datas(self):
        datas = [self._bus.read_byte_data(self._address, 0x28 + i) for i in range(5)]  # [0:3]が気圧、[3:5]が気温のデータ
        return datas[0:3], datas[3:5]

    def __convert_pressure(self, data):
        return (data[2] << 16 | data[1] << 8 | data[0]) / 4096

    def __convert_temperature(self, data):
        return 42.5 + ((data[1] << 8 | data[0]) - 65535) / 480

    def __convert_altitude(self, press, temp):
        altimeter_setting_mbar = 1013.25
        return ((pow(press / altimeter_setting_mbar, 0.190263) - 1) * temp) / 0.0065


class TemperatureHumiditySensor(I2CSensorBase):
    """
    温湿度センサーを表すクラス

    Attributes
    ----------
    type : str
        センサーの種類(温湿度センサー)
    model_number : str
        センサーの型番
    measured_time : multiprocessing.sharedctypes.Synchronized(ctypes.c_bool)
        現在保持しているデータを取得した時間
    temperature_celsius : multiprocessing.sharedctypes.Synchronized(ctypes.c_bool)
        温度[℃]
    humidity_percent : multiprocessing.sharedctypes.Synchronized(ctypes.c_bool)
        空気中の湿度[%]
    _bus : smbus2.SMBus
        i2cのバス
    _address : int
        センサーのi2cアドレス
    _is_active : multiprocessing.sharedctypes.Synchronized(ctypes.c_bool)
        センサが値を更新しているか(問題なく動いているか)
    _p : multiprocessing.Process
        センサーの値を取得してメンバを更新していく並列プロセス
    """

    def __init__(self, address=0x45):
        """
        センサ情報を登録してから、セットアップとデータ更新プロセスを開始する

        Parameters
        ----------
        _address : int, default 0x45
            センサーのi2cアドレス
        """
        self.type = "temperature_humidity_sensor"
        self.model_number = "SHT31"
        self.measured_time = Value("d", 0.0)
        self.temperature_celsius = Value("d", 0.0)
        self.humidity_percent = Value("d", 0.0)
        super().__init__(address)

    def _setup(self):
        self._bus.write_byte_data(self._address, 0x21, 0x30)

    def _update(self):
        temp, humid = self.__read_datas()

        self.measured_time.value = time()
        self.temperature_celsius.value = self.__convert_temperature(temp)
        self.humidity_percent.value = self.__convert_humidity(humid)

    def __read_datas(self):
        self._bus.write_byte_data(self._address, 0xE0, 0x00)
        datas = self._bus.read_i2c_block_data(self._address, 0x00, 6)  # [0:2]が気温、[3:5]が湿度のデータ
        return (datas[0:2]), (datas[3:5])

    def __convert_temperature(self, data):
        msb, lsb = data
        mlsb = ((msb << 8) | lsb)
        return (-45 + 175 * int(str(mlsb), 10) / (pow(2, 16) - 1))

    def __convert_humidity(self, data):
        msb, lsb = data
        mlsb = ((msb << 8) | lsb)
        return (100 * int(str(mlsb), 10) / (pow(2, 16) - 1))


class PulseWaveSensor(I2CSensorBase):
    """
    脈波センサーを表すクラス

    Attributes
    ----------
    type : str
        センサーの種類(脈波センサー)
    model_number : str
        センサーの型番
    measured_time : multiprocessing.sharedctypes.Synchronized(ctypes.c_bool)
        現在保持しているデータを取得した時間
    heart_bpm_fifo_1204hz : multiprocessing.sharedctypes.Synchronized(ctypes.c_bool)
        脈波の値
    _bus : smbus2.SMBus
        i2cのバス
    _address : int
        センサーのi2cアドレス
    _is_active : multiprocessing.sharedctypes.Synchronized(ctypes.c_bool)
        センサが値を更新しているか(問題なく動いているか)
    _p : multiprocessing.Process
        センサーの値を取得してメンバを更新していく並列プロセス

    Notes
    -----
    外部ライブラリを使うのでアドレスやSMBusは渡さない
    """

    def __init__(self):
        """
        センサ情報を登録してから、セットアップとデータ更新プロセスを開始する
        """
        self.type = "pulse_wave_sensor"
        self.model_number = "BH1792GLC"
        self.measured_time = Value("d", 0.0)
        self.heart_bpm_fifo_1204hz = Value("d", 0.0)
        super().__init__(None)

    def _setup(self):
        self._bus.close()  # 接続に外部ライブラリを使っているのでI2Cバスを閉じる
        self._drv = BH1792GLCDriver()
        self._drv.reset()
        self._drv.probe()

    def _update(self):
        beat = self.__read_datas()

        self.measured_time.value = time()
        self.heart_bpm_fifo_1204hz.value = self.__convert_heartbeat(beat)

    def __read_datas(self):
        return self._drv.measure_single_get()

    def __convert_heartbeat(self, data):
        return float(data[0])


class Thermistor(SerialSensorBase):
    """
    サーミスターを表すクラス

    Attributes
    ----------
    type : str
        センサーの種類(サーミスター)
    model_number : str
        センサーの型番
    measured_time : multiprocessing.sharedctypes.Synchronized(ctypes.c_bool)
        現在保持しているデータを取得した時間
    temperature_celsius : multiprocessing.sharedctypes.Synchronized(ctypes.c_bool)
        摂氏温度[℃]
    _ser : serial.Serial
        シリアルポート
    _signal : str
        シリアルで送る文字。一桁の数字
    _lock : multiprocessing.Lock
        Lockインスタンス
    _is_active : multiprocessing.sharedctypes.Synchronized(ctypes.c_bool)
        センサが値を更新しているか(問題なく動いているか)
    _p : multiprocessing.Process
        センサーの値を取得してメンバを更新していく並列プロセス
    """

    def __init__(self, signal, lock):
        """
        センサ情報を登録してから、セットアップとデータ更新プロセスを開始する

        Parameters
        ----------
        signal : str
            シリアル通信で送るシグナル
        lock : multiprocessing.Lock
            メモリ保護のためのロック機構
        """
        self.type = "thermistor"
        self.model_number = "103JT-050"
        self.measured_time = Value("d", 0.0)
        self.temperature_celsius = Value("d", 0.0)
        super().__init__(signal, lock)

    def _setup(self):
        self._lock.acquire()
        sleep(1.5)
        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()
        self._lock.release()

    def _update(self):
        if self._retry > 3:
            self._close()
        temp = self.__read_datas()
        try:
            self.temperature_celsius.value = self.__convert_temperature(temp)
        except ValueError:  # シリアルでうまく文字列が受け取れなかった場合、リトライする
            self._retry += 1
            self._update()
        else:
            self._retry = 0
            self.measured_time.value = time()

    def __read_datas(self):
        self._lock.acquire()
        self._ser.write(bytes(self._signal, "utf-8"))
        datas = self._ser.readline()
        self._lock.release()
        return datas.decode("utf-8").rstrip()

    def __convert_temperature(self, data):
        return float(data)


class Accelerometer(SerialSensorBase):
    """
    加速度センサーを表すクラス

    Attributes
    ----------
    type : str
        センサーの種類(加速度センサー)
    model_number : str
        センサーの型番
    measured_time : multiprocessing.sharedctypes.Synchronized(ctypes.c_bool)
        現在保持しているデータを取得した時間
    accelerometer_x_mps2 : multiprocessing.sharedctypes.Synchronized(ctypes.c_bool)
        x軸方向の加速度
    accelerometer_y_mps2 : multiprocessing.sharedctypes.Synchronized(ctypes.c_bool)
        y軸方向の加速度
    accelerometer_z_mps2 : multiprocessing.sharedctypes.Synchronized(ctypes.c_bool)
        z軸方向の加速度
    _ser : serial.Serial
        シリアルポート
    _signal : str
        シリアルで送る文字。一桁の数字
    _lock : multiprocessing.Lock
        Lockインスタンス
    _is_active : multiprocessing.sharedctypes.Synchronized(ctypes.c_bool)
        センサが値を更新しているか(問題なく動いているか)
    _p : multiprocessing.Process
        センサーの値を取得してメンバを更新していく並列プロセス
    """

    def __init__(self, signal, lock):
        """
        センサ情報を登録してから、セットアップとデータ更新プロセスを開始する

        Parameters
        ----------
        signal : str
            シリアル通信で送るシグナル
        lock : multiprocessing.Lock
            メモリ保護のためのロック機構
        """
        self.type = "accelerometer"
        self.model_number = "KX224-1053"
        self.measured_time = Value("d", 0.0)
        self.accelerometer_x_mps2 = Value("d", 0.0)
        self.accelerometer_y_mps2 = Value("d", 0.0)
        self.accelerometer_z_mps2 = Value("d", 0.0)
        super().__init__(signal, lock)

    def _setup(self):
        self._lock.acquire()
        sleep(1.5)
        self._ser.reset_input_buffer()
        self._ser.reset_output_buffer()
        self._lock.release()

    def _update(self):
        if self._retry > 3:
            self._close()
        x, y, z = self.__read_datas()
        try:
            self.accelerometer_x_mps2.value = self.__convert_acceleration(x)
            self.accelerometer_y_mps2.value = self.__convert_acceleration(y)
            self.accelerometer_z_mps2.value = self.__convert_acceleration(z)
        except ValueError:  # シリアルでうまく文字列が受け取れなかった場合、リトライする
            self._retry += 1
            self._update()
        else:
            self._retry = 0
            self.measured_time.value = time()

    def __read_datas(self):
        self._lock.acquire()
        self._ser.write(bytes(self._signal, "utf-8"))
        datas = self._ser.readline()
        self._lock.release()
        return datas.decode("utf-8").rstrip().split(",")

    def __convert_acceleration(self, data):
        return float(data)
