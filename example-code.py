guion_don_quijote = {"linea_1":"sí, como ninguna otra", 
                    "linea_2":"Gracias.", 
                    "linea_3":"Sancho, prepárate para pelear contra los gigantes de muchos brazos.", 
                    "linea_4":"tra-la-la-la-la",
                    "linea_5":"No permitas que deje de brillar",
                    "linea_6":"Pues mis sueños vas a derrumbar",
                    "linea_7":"Mira Sancho, más allá",
                    "linea_8":"Son gigantes que te tengo que acabar.",
                    "linea_9":"Mira Sancho esta vez",
                    "linea_10":"Ahora no voy a retroceder",
                    "linea_11":"Pues los malos van a arder",
                    "linea_12":"Con mi espada voy a rebanar",
                    "linea_13":"Cada parte de su andar.",
                    "linea_14":"¡Ay Sancho! ¡Deja de molestar!",
                    "linea_15":"Pues con mi triunfo vas a acabar",
                    "linea_16":"¡Ay Sancho! No te faltó razón",
                    "linea_17":"Porque no sé, a qué camino voy",}

def responser(numLinea):
    line = "linea_" + str(numLinea)
    response = guion_don_quijote.get(line)
    return response

print(responser(3))