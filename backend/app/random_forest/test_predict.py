from backend.app.random_forest.predictor import (
    RandomForestPredictor
)

features = {
    "URLLength": 30,
    "DomainLength": 15,
    "IsDomainIP": 0,
    "TLDLength": 3,
    "NoOfSubDomain": 1,
    "HasObfuscation": 0,
    "NoOfObfuscatedChar": 0,
    "ObfuscationRatio": 0,
    "NoOfLettersInURL": 20,
    "LetterRatioInURL": 0.7,
    "NoOfDegitsInURL": 2,
    "DegitRatioInURL": 0.1,
    "NoOfEqualsInURL": 0,
    "NoOfQMarkInURL": 0,
    "NoOfAmpersandInURL": 0,
    "NoOfOtherSpecialCharsInURL": 1,
    "SpacialCharRatioInURL": 0.03,
    "IsHTTPS": 1
}

result = RandomForestPredictor.predict(
    features
)

print(result)