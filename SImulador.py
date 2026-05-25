from flask import Flask, request, render_template

app = Flask(__name__)

# --- PARÂMETROS 2026 ---
IAS = 537.13
LIMITE_DISPENSA_IRS = 15000.00

# --- TABELAS DE RETENÇÃO NA FONTE 2026 (Continente - Cat. A - Sem dependentes) ---
def calcular_retencao_cat_a(salario):
    if salario <= 920:
        taxa = 0.0
        parcela = 0.0
    elif salario <= 1042:
        taxa = 0.125
        parcela = 0.125 * 2.6 * (1273.85 - salario)
    elif salario <= 1108:
        taxa = 0.157
        parcela = 0.157 * 1.35 * (1554.83 - salario)
    elif salario <= 1154:
        taxa = 0.157
        parcela = 94.71
    elif salario <= 1212:
        taxa = 0.212
        parcela = 158.18
    elif salario <= 1819:
        taxa = 0.241
        parcela = 193.33
    elif salario <= 2114:
        taxa = 0.311
        parcela = 320.66
    elif salario <= 2603:
        taxa = 0.349
        parcela = 400.99
    elif salario <= 3824:
        taxa = 0.3836
        parcela = 491.07
    else:
        taxa = 0.3969
        parcela = 541.93

    retencao = (salario * taxa) - parcela
    return max(0, retencao)

def calcular_desconto_jovem(retencao, aplica_jovem, ano_jovem):
    if not aplica_jovem:
        return retencao
    
    if ano_jovem == 1: fator = 0.0
    elif 2 <= ano_jovem <= 4: fator = 0.25
    elif 5 <= ano_jovem <= 7: fator = 0.50
    elif 8 <= ano_jovem <= 10: fator = 0.75
    else: fator = 1.0

    return retencao * fator

def calcular_simulacao_mensal(bruto_a, bruto_b, aplica_jovem, ano_jovem, taxa_b_str):
    # 1. SEGURANÇA SOCIAL
    ss_a = bruto_a * 0.11
    ss_b = 0
    
    if bruto_b > 0:
        rendimento_relevante_b = bruto_b * 0.70
        
        # Teste de Acumulação: A Categoria A cobre o IAS?
        if bruto_a >= IAS:
            # Tem direito à isenção até 4x IAS no rendimento relevante mensal
            limite_isencao_b = 4 * IAS
            if rendimento_relevante_b > limite_isencao_b:
                ss_b = (rendimento_relevante_b - limite_isencao_b) * 0.214
        else:
            # Não ganha o suficiente em Cat A, paga SS normal em Cat B
            ss_b = rendimento_relevante_b * 0.214
            
    ss_total = ss_a + ss_b

    # 2. RETENÇÃO NA FONTE (IRS)
    irs_bruto_a = calcular_retencao_cat_a(bruto_a) if bruto_a > 0 else 0
    
    # A Lógica Automática da Categoria B (< 15.000€ anuais)
    if taxa_b_str == 'auto':
        estimativa_anual_b = bruto_b * 12
        if estimativa_anual_b < LIMITE_DISPENSA_IRS:
            taxa_b = 0.0
        else:
            taxa_b = 0.23
    elif taxa_b_str == 'isento':
        taxa_b = 0.0
    else:
        taxa_b = float(taxa_b_str) / 100.0

    irs_bruto_b = bruto_b * taxa_b if bruto_b > 0 else 0
    irs_bruto_total = irs_bruto_a + irs_bruto_b

    # 3. IRS JOVEM (Desconto mensal)
    irs_pago_a = calcular_desconto_jovem(irs_bruto_a, aplica_jovem, ano_jovem)
    irs_pago_b = calcular_desconto_jovem(irs_bruto_b, aplica_jovem, ano_jovem)
    irs_pago_total = irs_pago_a + irs_pago_b

    isencao_jovem = irs_bruto_total - irs_pago_total

    # 4. TOTAIS LÍQUIDOS E TAXAS EFETIVAS
    bruto_total = bruto_a + bruto_b
    liquido = bruto_total - ss_total - irs_pago_total
    
    taxa_efetiva = ((ss_total + irs_pago_total) / bruto_total * 100) if bruto_total > 0 else 0
    taxa_ss_a = (ss_a / bruto_a * 100) if bruto_a > 0 else 0
    taxa_ss_b = (ss_b / bruto_b * 100) if bruto_b > 0 else 0

    return {
        'bruto_total': bruto_total,
        'bruto_a': bruto_a,
        'bruto_b': bruto_b,
        'ss_total': ss_total,
        'ss_a': ss_a,
        'ss_b': ss_b,
        'taxa_ss_a': taxa_ss_a,
        'taxa_ss_b': taxa_ss_b,
        'irs_bruto_total': irs_bruto_total,
        'irs_pago_total': irs_pago_total,
        'irs_a': irs_pago_a,
        'irs_b': irs_pago_b,
        'isencao_jovem': isencao_jovem,
        'taxa_aplicada_b': taxa_b * 100,
        'liquido': liquido,
        'taxa_efetiva': taxa_efetiva
    }

@app.route('/', methods=['GET', 'POST'])
def index():
    sim_1 = None
    sim_2 = None
    
    if request.method == 'POST':
        # --- Cenário 1 ---
        b_a_1 = float(request.form.get('bruto_a_1', 0))
        b_b_1 = float(request.form.get('bruto_b_1', 0))
        j_1 = request.form.get('jovem_1') is not None
        a_1 = int(request.form.get('ano_jovem_1', 1))
        tx_1 = request.form.get('taxa_b_1', 'auto')
        
        sim_1 = calcular_simulacao_mensal(b_a_1, b_b_1, j_1, a_1, tx_1)

        # --- Cenário 2 ---
        b_a_2 = float(request.form.get('bruto_a_2', 0))
        b_b_2 = float(request.form.get('bruto_b_2', 0))
        j_2 = request.form.get('jovem_2') is not None
        a_2 = int(request.form.get('ano_jovem_2', 1))
        tx_2 = request.form.get('taxa_b_2', 'auto')
        
        sim_2 = calcular_simulacao_mensal(b_a_2, b_b_2, j_2, a_2, tx_2)

    return render_template('Mariana.html', sim_1=sim_1, sim_2=sim_2)

if __name__ == '__main__':
    app.run(debug=True)