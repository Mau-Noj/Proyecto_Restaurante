from django.db import migrations

CREATE_FUNCTION = """
CREATE OR REPLACE FUNCTION attendance_prevent_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'Los registros de asistencia son de solo lectura una vez creados (append-only). Usa un ajuste en vez de editar/borrar.';
END;
$$ LANGUAGE plpgsql;
"""

DROP_FUNCTION = "DROP FUNCTION IF EXISTS attendance_prevent_mutation() CASCADE;"

CREATE_TRIGGERS = """
CREATE TRIGGER attendance_timeentry_append_only
BEFORE UPDATE OR DELETE ON attendance_timeentry
FOR EACH ROW EXECUTE FUNCTION attendance_prevent_mutation();

CREATE TRIGGER attendance_timeentryadjustment_append_only
BEFORE UPDATE OR DELETE ON attendance_timeentryadjustment
FOR EACH ROW EXECUTE FUNCTION attendance_prevent_mutation();
"""

DROP_TRIGGERS = """
DROP TRIGGER IF EXISTS attendance_timeentry_append_only ON attendance_timeentry;
DROP TRIGGER IF EXISTS attendance_timeentryadjustment_append_only ON attendance_timeentryadjustment;
"""


class Migration(migrations.Migration):
    """Refuerzo a nivel de base de datos: incluso si algún día el código de
    la aplicación tuviera un bug o alguien entrara directo a la base, un
    UPDATE/DELETE sobre estas dos tablas se rechaza siempre. La app nunca
    necesita hacer ninguno de los dos (son de solo-INSERT por diseño), así
    que esto no debería afectar ninguna operación normal."""

    dependencies = [("attendance", "0001_initial")]

    operations = [
        migrations.RunSQL(CREATE_FUNCTION, DROP_FUNCTION),
        migrations.RunSQL(CREATE_TRIGGERS, DROP_TRIGGERS),
    ]
