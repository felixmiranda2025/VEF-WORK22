import { neon } from '@neondatabase/serverless';

export async function handler(event) {
    if (event.httpMethod !== 'POST') {
        return { statusCode: 405, body: 'Method Not Allowed' };
    }

    const sql = neon(process.env.DATABASE_URL);
    
    try {
        const { cliente_id, nombre, descripcion, fecha_inicio, fecha_entrega, estatus, monto_total, notas } = JSON.parse(event.body);
        
        if (!cliente_id || !nombre) {
            return {
                statusCode: 400,
                body: JSON.stringify({ success: false, error: 'Cliente y nombre son requeridos' })
            };
        }
        
        const result = await sql`
            INSERT INTO proyectos (
                cliente_id, nombre, descripcion, fecha_inicio, 
                fecha_entrega, estatus, monto_total, notas
            ) VALUES (
                ${cliente_id}, ${nombre}, ${descripcion || null}, 
                ${fecha_inicio || null}, ${fecha_entrega || null}, 
                ${estatus || 'activo'}, ${monto_total || 0}, ${notas || null}
            ) RETURNING *
        `;
        
        return {
            statusCode: 200,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                success: true,
                proyecto: result[0]
            })
        };
        
    } catch (error) {
        console.error('Error creando proyecto:', error);
        return {
            statusCode: 500,
            body: JSON.stringify({ success: false, error: error.message })
        };
    }
}