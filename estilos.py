import streamlit as st

def aplicar_estilos_personalizados():
    """Inyecta CSS Premium unificado para el Proyecto Nehemías (Python-Native)."""
    st.markdown("""
        <style>
        /* Importar Poppins desde Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap');
        
        /* Variables de Sistema de Diseño */
        :root {
            --verde-principal: #018d38;
            --verde-oscuro: #0b5640;
            --verde-menta: #3AF9A2;
            --azul-institucional: #3561ab;
            --naranja-alerta: #f28e18;
            --gris-fondo: #f8fafc;
            --gris-borde: #e2e8f0;
            --blanco: #ffffff;
            --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
            --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
        }

        /* Tipografía Global */
        html, body, [class*="css"]  {
            font-family: 'Poppins', sans-serif !important;
            background-color: var(--gris-fondo);
        }

        h1, h2, h3, h4, h5, h6 {
            font-weight: 700 !important;
            color: var(--verde-oscuro) !important;
            letter-spacing: -0.025em;
        }

        /* Estilo Premium de la Barra Lateral */
        [data-testid="stSidebar"] {
            background-color: var(--blanco) !important;
            border-right: 1px solid var(--gris-borde) !important;
        }
        
        [data-testid="stSidebarNav"] {
            padding-top: 2rem !important;
        }

        /* Personalización de Radio Buttons en Sidebar */
        [data-testid="stSidebar"] .st-eb {
            background-color: transparent !important;
        }

        /* Botones Estilizados */
        .stButton>button {
            width: 100%;
            background-color: var(--verde-principal) !important;
            color: white !important;
            border-radius: 8px !important;
            border: none !important;
            padding: 0.6rem 1.2rem !important;
            font-weight: 600 !important;
            font-size: 0.95rem !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: var(--shadow-sm) !important;
        }
        
        .stButton>button:hover {
            transform: translateY(-1px);
            box-shadow: var(--shadow-md) !important;
            background-color: var(--verde-oscuro) !important;
            opacity: 0.9;
        }

        .stButton>button:active {
            transform: translateY(0px);
        }

        /* Inputs y Selects */
        .stTextInput>div>div>input, .stSelectbox>div>div>div, .stTextArea>div>div>textarea {
            border-radius: 8px !important;
            border: 1px solid var(--gris-borde) !important;
            background-color: white !important;
            transition: border-color 0.2s;
        }
        
        .stTextInput>div>div>input:focus {
            border-color: var(--verde-principal) !important;
        }

        /* Contenedores de Actividad (Cards) */
        [data-testid="stVerticalBlock"] > div > div > [data-testid="stVerticalBlock"] {
            /* Estilo para los contenedores con border=True de Streamlit */
        }
        
        div.stContainer {
            background-color: white;
            border-radius: 12px !important;
            padding: 1.5rem !important;
            border: 1px solid var(--gris-borde) !important;
            box-shadow: var(--shadow-sm) !important;
            margin-bottom: 1rem !important;
        }

        /* Badges de Estado Premium */
        .badge {
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            display: inline-block;
        }
        .badge-activa { background-color: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
        .badge-cerrada { background-color: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
        .badge-anulada { background-color: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; }
        .badge-revision { background-color: #fef3c7; color: #92400e; border: 1px solid #fde68a; }

        /* Métricas del Dashboard */
        [data-testid="stMetric"] {
            background-color: white !important;
            padding: 1.2rem !important;
            border-radius: 12px !important;
            border: 1px solid var(--gris-borde) !important;
            box-shadow: var(--shadow-sm) !important;
        }
        
        [data-testid="stMetricValue"] {
            font-weight: 700 !important;
            color: var(--verde-oscuro) !important;
            font-size: 1.8rem !important;
        }
        
        [data-testid="stMetricLabel"] {
            font-weight: 600 !important;
            color: #64748b !important;
            font-size: 0.85rem !important;
            text-transform: uppercase;
            letter-spacing: 0.025em;
        }

        /* Tablas y Editores de Datos */
        .stDataFrame, [data-testid="stTable"] {
            border-radius: 12px !important;
            overflow: hidden !important;
            border: 1px solid var(--gris-borde) !important;
        }

        /* Mensajes de Alerta */
        .stAlert {
            border-radius: 12px !important;
            border: none !important;
            box-shadow: var(--shadow-sm) !important;
        }

        /* Expander Stylization */
        .streamlit-expanderHeader {
            font-weight: 600 !important;
            color: var(--verde-oscuro) !important;
            background-color: transparent !important;
        }
        
        .streamlit-expanderContent {
            border-top: 1px solid var(--gris-borde) !important;
            padding-top: 1rem !important;
        }

        /* Ocultar elementos innecesarios */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        /* Eliminamos la ocultación del header para no perder el botón del sidebar */
        </style>
    """, unsafe_allow_html=True)
