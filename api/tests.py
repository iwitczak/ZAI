from datetime import timedelta

from django.db import DataError, IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from api.models import Measurement, Sensor, Series


def make_series(name="Temperatura", **kwargs):
    defaults = dict(min_value=0.0, max_value=100.0, color="#FF0000", icon="thermo", unit="C")
    defaults.update(kwargs)
    return Series.create_series(name=name, **defaults)


def make_measurement(sensor, value, timestamp):
    """
    Timestamp w Measurement ma auto_now_add=True, więc create() ignoruje
    przekazaną wartość. Ustawiamy ją przez update(), który omija auto_now_add.
    """
    m = Measurement.objects.create(sensor=sensor, value=value)
    Measurement.objects.filter(pk=m.pk).update(timestamp=timestamp)
    m.refresh_from_db()
    return m


# ---------------------------------------------------------------- Series
class SeriesTests(TestCase):
    def test_create_series(self):
        s = make_series()
        self.assertIsNotNone(s.pk)
        self.assertEqual(s.name, "Temperatura")
        self.assertEqual(Series.objects.count(), 1)

    def test_get_all_series(self):
        make_series("A")
        make_series("B")
        self.assertEqual({s.name for s in Series.get_all_series()}, {"A", "B"})

    def test_get_all_series_empty(self):
        self.assertEqual(Series.get_all_series().count(), 0)

    def test_get_series_by_id(self):
        s = make_series()
        self.assertEqual(Series.get_series_by_id(s.pk), s)

    def test_get_series_by_id_missing_returns_none(self):
        self.assertIsNone(Series.get_series_by_id(9999))

    def test_update_series_returns_number_of_updated_rows(self):
        s = make_series()
        updated = Series.update_series(s.pk, "Nowa", 1.0, 50.0, "#00FF00", icon="x", unit="K")
        self.assertEqual(updated, 1)
        s.refresh_from_db()
        self.assertEqual((s.name, s.min_value, s.max_value, s.color, s.icon, s.unit),
                         ("Nowa", 1.0, 50.0, "#00FF00", "x", "K"))

    def test_update_series_missing_returns_zero(self):
        self.assertEqual(Series.update_series(9999, "N", 0, 1, "#000000"), 0)

    def test_update_series_without_icon_and_unit_clears_them(self):
        s = make_series(icon="thermo", unit="C")
        Series.update_series(s.pk, "A", 0, 10, "#000000")
        s.refresh_from_db()
        self.assertIsNone(s.icon)
        self.assertIsNone(s.unit)

    def test_delete_series(self):
        s = make_series()
        Series.delete_series(s.pk)
        self.assertEqual(Series.objects.count(), 0)

    def test_delete_series_cascades_to_sensors_and_measurements(self):
        s = make_series()
        sensor, _ = Sensor.create_sensor("S1", s.pk)
        make_measurement(sensor, 1.0, timezone.now())
        Series.delete_series(s.pk)
        self.assertEqual(Sensor.objects.count(), 0)
        self.assertEqual(Measurement.objects.count(), 0)

    def test_constraint_min_must_be_lower_than_max(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_series(min_value=10.0, max_value=10.0)
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_series(min_value=20.0, max_value=10.0)

    def test_constraint_valid_hex_color(self):
        for bad in ["red", "FF0000", "#FF00", "#GG0000", "#FF00000"]:
            with self.subTest(color=bad):
                with self.assertRaises((IntegrityError, DataError)), transaction.atomic():
                    make_series(color=bad)

    def test_valid_hex_color_lower_and_upper_case(self):
        make_series("A", color="#abcdef")
        make_series("B", color="#ABCDEF")
        self.assertEqual(Series.objects.count(), 2)

    def test_name_validator_runs_on_full_clean(self):
        from django.core.exceptions import ValidationError
        s = Series(name="", min_value=0, max_value=1, color="#000000")
        with self.assertRaises(ValidationError):
            s.full_clean()


# ---------------------------------------------------------------- Sensor
class SensorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.series = make_series()

    def test_create_sensor_returns_sensor_and_raw_key(self):
        sensor, raw_key = Sensor.create_sensor("S1", self.series.pk)
        self.assertIsNotNone(sensor.pk)
        self.assertTrue(raw_key)
        self.assertEqual(sensor.series_id, self.series.pk)
        self.assertTrue(sensor.is_active)

    def test_create_sensor_stores_hash_not_raw_key(self):
        sensor, raw_key = Sensor.create_sensor("S1", self.series.pk)
        stored = Sensor.objects.get(pk=sensor.pk)
        self.assertNotEqual(stored.api_key_hash, raw_key)
        self.assertEqual(stored.api_key_hash, Sensor._get_api_key_hash(raw_key))
        self.assertEqual(len(stored.api_key_hash), 64)

    def test_create_sensor_hides_hash_on_returned_object(self):
        sensor, _ = Sensor.create_sensor("S1", self.series.pk)
        self.assertIsNone(sensor.api_key_hash)

    def test_generated_keys_are_unique(self):
        _, k1 = Sensor.create_sensor("S1", self.series.pk)
        _, k2 = Sensor.create_sensor("S2", self.series.pk)
        self.assertNotEqual(k1, k2)

    def test_hash_is_deterministic(self):
        self.assertEqual(Sensor._get_api_key_hash("abc"), Sensor._get_api_key_hash("abc"))
        self.assertNotEqual(Sensor._get_api_key_hash("abc"), Sensor._get_api_key_hash("abd"))

    def test_get_sensor_by_api_key(self):
        sensor, raw_key = Sensor.create_sensor("S1", self.series.pk)
        self.assertEqual(Sensor.get_sensor_by_api_key(raw_key).pk, sensor.pk)

    def test_get_sensor_by_api_key_wrong_key_returns_none(self):
        Sensor.create_sensor("S1", self.series.pk)
        self.assertIsNone(Sensor.get_sensor_by_api_key("zly-klucz"))

    def test_get_all_sensors_empty(self):
        self.assertEqual(Sensor.get_all_sensors().count(), 0)

    def test_get_all_sensors_annotates_last_measurement(self):
        s1, _ = Sensor.create_sensor("S1", self.series.pk)
        s2, _ = Sensor.create_sensor("S2", self.series.pk)
        now = timezone.now()
        make_measurement(s1, 1.0, now - timedelta(hours=2))
        make_measurement(s1, 2.0, now)
        make_measurement(s2, 3.0, now - timedelta(hours=1))

        result = {s.name: s.last_measurement_at for s in Sensor.get_all_sensors()}
        self.assertEqual(result["S1"], now)
        self.assertEqual(result["S2"], now - timedelta(hours=1))

    def test_get_all_sensors_sensor_without_measurements_has_none(self):
        Sensor.create_sensor("S1", self.series.pk)
        sensor = Sensor.get_all_sensors().get()
        self.assertIsNone(sensor.last_measurement_at)

    def test_get_all_sensors_does_not_duplicate_rows(self):
        s1, _ = Sensor.create_sensor("S1", self.series.pk)
        for i in range(5):
            make_measurement(s1, float(i), timezone.now())
        self.assertEqual(Sensor.get_all_sensors().count(), 1)

    def test_get_all_sensors_single_query(self):
        s1, _ = Sensor.create_sensor("S1", self.series.pk)
        make_measurement(s1, 1.0, timezone.now())
        with self.assertNumQueries(1):
            list(Sensor.get_all_sensors())

    def test_get_sensor_by_id_returns_dict_with_expected_keys(self):
        sensor, _ = Sensor.create_sensor("S1", self.series.pk)
        now = timezone.now()
        make_measurement(sensor, 1.0, now)

        result = Sensor.get_sensor_by_id(sensor.pk)
        self.assertEqual(set(result), {"id", "name", "series", "created_at", "last_measurement_at"})
        self.assertEqual(result["id"], sensor.pk)
        self.assertEqual(result["name"], "S1")
        self.assertEqual(result["series"], self.series.pk)
        self.assertEqual(result["last_measurement_at"], now)

    def test_get_sensor_by_id_does_not_leak_api_key_hash(self):
        sensor, _ = Sensor.create_sensor("S1", self.series.pk)
        self.assertNotIn("api_key_hash", Sensor.get_sensor_by_id(sensor.pk))

    def test_get_sensor_by_id_no_measurements(self):
        sensor, _ = Sensor.create_sensor("S1", self.series.pk)
        self.assertIsNone(Sensor.get_sensor_by_id(sensor.pk)["last_measurement_at"])

    def test_get_sensor_by_id_missing_returns_none(self):
        self.assertIsNone(Sensor.get_sensor_by_id(9999))

    def test_get_sensor_by_id_ignores_other_sensors_measurements(self):
        s1, _ = Sensor.create_sensor("S1", self.series.pk)
        s2, _ = Sensor.create_sensor("S2", self.series.pk)
        make_measurement(s2, 1.0, timezone.now())
        self.assertIsNone(Sensor.get_sensor_by_id(s1.pk)["last_measurement_at"])

    def test_unregister_sensor(self):
        sensor, _ = Sensor.create_sensor("S1", self.series.pk)
        self.assertEqual(Sensor.unregister_sensor(sensor.pk), 1)
        sensor.refresh_from_db()
        self.assertFalse(sensor.is_active)

    def test_unregister_sensor_missing_returns_zero(self):
        self.assertEqual(Sensor.unregister_sensor(9999), 0)

    def test_unregister_does_not_delete_measurements(self):
        sensor, _ = Sensor.create_sensor("S1", self.series.pk)
        make_measurement(sensor, 1.0, timezone.now())
        Sensor.unregister_sensor(sensor.pk)
        self.assertEqual(Measurement.objects.count(), 1)


    def test_inactive_sensor_cannot_be_found_by_api_key(self):
        sensor, raw_key = Sensor.create_sensor("S1", self.series.pk)
        Sensor.unregister_sensor(sensor.pk)
        self.assertIsNone(Sensor.get_sensor_by_api_key(raw_key))

    def test_delete_sensor_cascades_to_measurements(self):
        sensor, _ = Sensor.create_sensor("S1", self.series.pk)
        make_measurement(sensor, 1.0, timezone.now())
        sensor.delete()
        self.assertEqual(Measurement.objects.count(), 0)


# ----------------------------------------------------------- Measurement
class MeasurementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.series_a = make_series("A")
        cls.series_b = make_series("B")
        cls.sensor_a, cls.key_a = Sensor.create_sensor("SA", cls.series_a.pk)
        cls.sensor_b, cls.key_b = Sensor.create_sensor("SB", cls.series_b.pk)
        cls.now = timezone.now()

    # --- create_measurement
    def test_create_measurement_valid_key(self):
        m = Measurement.create_measurement(self.key_a, 12.5, self.now)
        self.assertIsNotNone(m)
        self.assertEqual(m.value, 12.5)
        self.assertEqual(m.sensor_id, self.sensor_a.pk)

    def test_create_measurement_invalid_key_returns_none(self):
        self.assertIsNone(Measurement.create_measurement("zly", 1.0, self.now))
        self.assertEqual(Measurement.objects.count(), 0)


    def test_create_measurement_respects_passed_timestamp(self):
        ts = self.now - timedelta(days=3)
        m = Measurement.create_measurement(self.key_a, 1.0, ts)
        m.refresh_from_db()
        self.assertEqual(m.timestamp, ts)

    def test_create_measurement_keeps_passed_timestamp(self):
        ts = self.now - timedelta(days=3)
        m = Measurement.create_measurement(self.key_a, 1.0, ts)
        m.refresh_from_db()
        self.assertEqual(m.timestamp, ts)

    # --- get_measurement_by_id
    def test_get_measurement_by_id(self):
        m = make_measurement(self.sensor_a, 7.0, self.now)
        result = Measurement.get_measurement_by_id(m.pk)
        self.assertEqual(result, {
            "id": m.pk,
            "value": 7.0,
            "timestamp": self.now,
            "sensor": self.sensor_a.pk,
            "sensor__series": self.series_a.pk,
        })

    def test_get_measurement_by_id_missing_returns_none(self):
        self.assertIsNone(Measurement.get_measurement_by_id(9999))

    # --- get_measurements
    def _fill(self):
        t = self.now
        self.m_old = make_measurement(self.sensor_a, 1.0, t - timedelta(hours=5))
        self.m_mid = make_measurement(self.sensor_a, 2.0, t - timedelta(hours=3))
        self.m_new = make_measurement(self.sensor_b, 3.0, t - timedelta(hours=1))

    def _range(self):
        return dict(from_timestamp=self.now - timedelta(days=1), to_timestamp=self.now)

    def test_get_measurements_all_series_when_empty_filter(self):
        self._fill()
        result = list(Measurement.get_measurements(**self._range()))
        self.assertEqual(len(result), 3)

    def test_get_measurements_filter_by_series(self):
        self._fill()
        result = Measurement.get_measurements(series=[self.series_a.pk], **self._range())
        self.assertEqual({m.pk for m in result}, {self.m_old.pk, self.m_mid.pk})

    def test_get_measurements_multiple_series(self):
        self._fill()
        result = Measurement.get_measurements(
            series=[self.series_a.pk, self.series_b.pk], **self._range())
        self.assertEqual(len(result), 3)

    def test_get_measurements_unknown_series_returns_empty(self):
        self._fill()
        result = Measurement.get_measurements(series=[9999], **self._range())
        self.assertEqual(len(result), 0)

    def test_get_measurements_time_range(self):
        self._fill()
        result = Measurement.get_measurements(
            from_timestamp=self.now - timedelta(hours=4),
            to_timestamp=self.now - timedelta(hours=2),
        )
        self.assertEqual([m.pk for m in result], [self.m_mid.pk])

    def test_get_measurements_range_is_inclusive(self):
        self._fill()
        result = Measurement.get_measurements(
            from_timestamp=self.m_old.timestamp, to_timestamp=self.m_new.timestamp)
        self.assertEqual(len(result), 3)

    def test_get_measurements_default_order_ascending(self):
        self._fill()
        result = list(Measurement.get_measurements(**self._range()))
        self.assertEqual([m.pk for m in result],
                         [self.m_old.pk, self.m_mid.pk, self.m_new.pk])

    def test_get_measurements_descending_order(self):
        self._fill()
        result = list(Measurement.get_measurements(order_by="-timestamp", **self._range()))
        self.assertEqual([m.pk for m in result],
                         [self.m_new.pk, self.m_mid.pk, self.m_old.pk])

    def test_get_measurements_order_by_value(self):
        self._fill()
        result = list(Measurement.get_measurements(order_by="-value", **self._range()))
        self.assertEqual([m.value for m in result], [3.0, 2.0, 1.0])

    def test_get_measurements_limit(self):
        self._fill()
        result = Measurement.get_measurements(limit=2, **self._range())
        self.assertEqual(len(result), 2)

    def test_get_measurements_limit_applies_after_ordering(self):
        self._fill()
        result = list(Measurement.get_measurements(order_by="-timestamp", limit=1, **self._range()))
        self.assertEqual(result[0].pk, self.m_new.pk)

    def test_get_measurements_empty_database(self):
        self.assertEqual(len(Measurement.get_measurements(**self._range())), 0)

