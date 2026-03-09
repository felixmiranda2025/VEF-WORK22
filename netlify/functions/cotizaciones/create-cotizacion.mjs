import { neon } from '@neondatabase/serverless';

export async function handler(event) {
    if (event.httpMethod !== 'POST') {
        return { statusCode: 405, body: 'Method Not Allowed' };
    }

    const sql = neon(process.env.DATABASE_URL);
    
    try {
        const { proyecto_id, cliente_id, fecha, validez_hasta, subtotal, iva, total, estatus, notas, created_by, items } = JSON.parse(event.body);
        
        if (!cliente_id) {
            return {
                statusCode: 400,
                body: JSON.stringify({ success: false, error: 'Cliente es requerido' })
            };
        }
        
        // Generar folio automático
        const folio = `COT-${Date.now()}`;
        
        // Iniciar transacción
        const result = await sql.begin(async (sql) => {
            // Insertar cotización
            const cotizacion = await sql`
                INSERT INTO cotizaciones (
                    folio, proyecto_id, cliente_id, fecha, validez_hasta,
                    subtotal, iva, total, estatus, notas, created_by
                ) VALUES (
                    ${folio}, ${proyecto_id || null}, ${cliente_id}, 
                    ${fecha || new Date().toISOString().split('T')[0]}, 
                    ${validez_hasta || null}, ${subtotal || 0}, ${iva || 0}, 
                    ${total || 0}, ${estatus || 'pendiente'}, ${notas || null}, 
                    ${created_by || null}
                ) RETURNING *
            `;
            
            // Insertar items si hay
            if (items && items.length > 0) {
                for (const item of items) {
                    await sql`
                        INSERT INTO items_cotizacion (
                            cotizacion_id, descripcion, cantidad, 
                            precio_unitario, importe, notas
                        ) VALUES (
                            ${cotizacion[0].id}, ${item.descripcion}, 
                            ${item.cantidad || 1}, ${item.precio_unitario || 0},
                            ${item.importe || (item.cantidad * item.precio_unitario) || 0},
                            ${item.notas || null}
                        )
                    `;
                }
            }
            
            return cotizacion[0];
        });
        
        return {
            statusCode: 200,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                success: true,
                cotizacion: result
            })
        };
        
    } catch (error) {
        console.error('Error creando cotización:', error);
        return {
            statusCode: 500,
            body: JSON.stringify({ success: false, error: error.message })
        };
    }
}